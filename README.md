# stove-uploader-mac

Upload game builds to **STOVE** (Smilegate's PC store) from macOS, using STOVE's own uploader.

STOVE ships its Uploader CLI for Windows only. The CLI, the Updater it downloads and the Core that
does the upload are PyInstaller packages of Python 3.11 bytecode, so they run on a native macOS
Python 3.11 with native dependencies and a few small patches. This repository contains **no
Smilegate code**: `setup.sh` downloads the official package from STOVE when you install.

Unofficial and not affiliated with Smilegate/STOVE. It runs STOVE's own client code unchanged, but
check STOVE's terms for your account before you rely on it.

**Status:** full uploads work. Tested 2026-10-21 on macOS (Apple Silicon) with Uploader CLI
v1.0.4.0, Core v1.0.4.0 and Updater v1.0.12.3: a 250 MB Unity Windows build uploaded in under a minute.

한국어 요약은 [아래](#한국어-요약)에 있습니다.

## Requirements

- macOS on Apple Silicon (Intel is untested)
- `curl`, `unzip`, and either [uv](https://docs.astral.sh/uv/) or `python3` with pip (used only to fetch uv)
- A STOVE **e-mail** account. Mobile OTP and third-party logins (Google, Naver, …) are not supported by the CLI.
- Optional: the **caller-detail key** from STOVE support, only if sign-in is refused (see [49500](#49500-blocked-ip-address-at-sign-in))

## Setup

```bash
git clone https://github.com/CodeOneLabs/stove-uploader-mac.git
cd stove-uploader-mac
./setup.sh
./stove-uploader --help
```

`setup.sh` puts Python 3.11 and everything it downloads inside this folder (all gitignored) and
does not touch your system Python. Run it again to pick up a new uploader version.

## Upload

Create `stove.local.env` (gitignored):

```bash
STOVE_GAME_ID=GM-XXXX-XXXXXXXX_IND
STOVE_USER=you@example.com
# Optional. Usually not needed in Korea; see 49500 below.
# STOVE_CALLER_DETAIL=<key from store.support@smilegate.com>
```

Store your password in the macOS Keychain once (it prompts for it):

```bash
security add-generic-password -s stove-uploader -a you@example.com -w
```

Then upload a Windows build folder:

```bash
./upload.sh /path/to/WindowsBuild "v1.0 demo"
```

The description is limited to 60 characters and defaults to `<folder> <date>`. `.DS_Store` files
and Unity's `*_BurstDebugInformation_DoNotShip` folder are excluded. Extra arguments go straight
to the uploader, for example `-ee pdb` to skip `.pdb` files. If no password is in the Keychain,
`upload.sh` asks for it.

When it finishes you get `Upload SUCCESS` and a link to the new build in STOVE Studio.

### Raw CLI

`./stove-uploader` accepts the official options; see
[STOVE's uploader CLI guide](https://studiodocs.super.site/build-management/uploader-cli).
Pass `-s` as an absolute path: the CLI resolves relative paths against its own folder.

## Troubleshooting

Every problem below came up while getting the first upload through. Logs are in
`.script_run_test/STOVEUploaderCLI/log/` and `.script_run_test/STOVEUploaderCLICore/log/<game id>/`
(passwords and tokens are masked, but your e-mail is in them).

### `49500 blocked IP address` at sign-in

Core log: `POST https://s-api.onstove.com/sign/v2.1/pc/signin` → `{'code': 49500, 'message': 'blocked IP address'}`,
then `SIGN_IN_CANNOT_RETRY_REQUEST` and exit code **118**.

The `-cd` / `--caller-detail` key is **optional**. STOVE's guide says it is not needed inside
Korea, and normally sign-in works without it.

In our case sign-in was refused this way on three different Korean networks, on two days, and
with the **official Windows CLI** on a Windows PC too. Our best guess is that the account was
blocked after repeated sign-in attempts while setting this tool up. We did not confirm the cause
with STOVE.

What got past it was the caller-detail key. If you hit 49500, stop retrying (more attempts may
extend the block), ask **store.support@smilegate.com** for the key (mention the 49500 error and
your game ID), and set `STOVE_CALLER_DETAIL`. STOVE issues the key on request, so don't publish it.

### `'protection' and 'prot_params' require a passphrase`

Core log: `http_check_build_continue_upload failed: ValueError(...)`, then
`Failed to get previous upload data: result is 1400` and exit code **120**.

pycryptodome 4.x rejects the RSA key export the uploader uses. The Core bundles 3.21.0.
`requirements-mac.txt` pins every library to the version bundled in the Windows Core
(boto3 1.35.99 for the S3 upload, requests 2.32.5 for the User-Agent, …). Don't loosen the pins
without testing. When STOVE ships a new Core, check its bundled versions again.

### `continue-upload` returns `500 INTERNAL SERVER ERROR`

Core log: `POST https://api.onstove.com/studio/v1/builds/continue-upload` → `{'code': 500, ...}`,
then `result is 1402` and exit code **122**. Sign-in worked just before it.

The game ID was wrong. The numeric product number (the one in STOVE Studio URLs,
`.../products/<number>/...`) is not the game ID. Use the ID that looks like `GM-XXXX-XXXXXXXX_IND`,
shown for the game in STOVE Studio. `upload.sh` warns when `STOVE_GAME_ID` doesn't start with `GM-`.

### `Failed to initialize Updater App: Failed to get version info.`

Outside a frozen .exe, the app reads its own version from `git tag` / `git rev-list`. `shim/git`
answers with the version that `patches/stove_mac.py` reads from the .exe's Windows version resource.

### `Failed to run STOVE Updater: PermissionError(13, 'Permission denied')`

The CLI downloads `STOVEUpdater.exe` and tries to execute it. `patches/sitecustomize.py` redirects
that call, and the later `STOVEUploaderCLICore.exe` call, to this Python running the exe's bytecode.

### macOS-only Python errors

- `psutil.AccessDenied` when the uploader scans processes: patched to return an empty list.
- `NotImplementedError` from `multiprocessing.Queue.qsize()` (macOS has no `sem_getvalue`):
  patched with a shared counter.

### uv tries to replace `~/.local/bin/python3.11`

`uv python install` also links the interpreter into `~/.local/bin`. `setup.sh` passes `--no-bin`
so your own Python setup is left alone.

## How it works

| Path | What it is |
| --- | --- |
| `setup.sh` | Installs Python 3.11 (via uv), downloads the official CLI and [pyinstxtractor](https://github.com/extremecoders-re/pyinstxtractor), installs `requirements-mac.txt`, unpacks the CLI into `runner/`. |
| `stove-uploader` | Launcher: Python 3.11 with `patches/`, `runner/` and `deps/` on the path and `shim/` on `PATH`. |
| `patches/sitecustomize.py` | macOS fixes plus the `subprocess.Popen` redirect for `STOVEUpdater.exe` / `STOVEUploaderCLICore.exe`. |
| `patches/stove_mac.py` | Unpacks an exe's bytecode into `updater_runner/` or `core_runner/` on first use, and again when the exe changes (the Updater replaces the Core when STOVE ships a new one). |
| `shim/git` | Version answers for the app's git lookup. |
| `upload.sh` | Convenience wrapper: settings file, Keychain password, exclusions. |

Flow: CLI → downloads the Updater into `runner/` → the Updater installs or updates the Core in
`runner/STOVEUploaderCLICore/` → the Core signs in, uploads to S3 and reports the build.

## License

MIT for the files in this repository. The STOVE Uploader that `setup.sh` downloads is Smilegate's
software, and pyinstxtractor (GPL-3.0) is downloaded at setup time; neither is part of this repository.

## 한국어 요약

STOVE 업로더 CLI는 Windows용만 배포됩니다. 이 도구는 공식 패키지를 내려받아 그 안의 Python 3.11
바이트코드를 macOS 네이티브 Python으로 실행합니다. 스마일게이트 코드는 저장소에 들어 있지 않습니다.

```bash
./setup.sh
# stove.local.env 에 STOVE_GAME_ID / STOVE_USER 작성 (STOVE_CALLER_DETAIL 은 선택)
security add-generic-password -s stove-uploader -a you@example.com -w
./upload.sh /path/to/WindowsBuild "v1.0 demo"
```

막혔던 것들:

- **`49500 blocked IP address`** (종료 코드 118): caller-detail(-cd) 키는 **선택 사항**이고, 국내에서는
  보통 없어도 로그인됩니다. 저희는 세팅하면서 로그인을 여러 번 시도하다 계정이 막힌 것으로 보입니다
  (STOVE에 원인을 확인하지는 않았습니다). 네트워크를 바꿔도, Windows 공식 CLI에서도 같았습니다.
  이 오류가 나면 재시도를 멈추고 store.support@smilegate.com 에 **caller-detail 키**를 요청해
  `STOVE_CALLER_DETAIL` 에 넣으세요. 요청해서 받는 키이니 공개하지 마세요.
- **`'protection' and 'prot_params' require a passphrase`** (결과 1400, 종료 코드 120): pycryptodome 4.x
  문제입니다. `requirements-mac.txt` 로 Windows 번들과 같은 버전(3.21.0 등)으로 고정했습니다.
- **`continue-upload` 500 INTERNAL SERVER ERROR** (결과 1402, 종료 코드 122): 게임 ID 자리에 Studio URL의
  숫자 상품 번호를 넣으면 이렇게 됩니다. `GM-XXXX-XXXXXXXX_IND` 형식의 게임 ID를 쓰세요.
- 그 밖에 Updater 버전 정보 오류, .exe 실행 권한 오류, macOS의 psutil·multiprocessing 차이는 패치로
  처리되어 있습니다.

비공식 도구이며 스마일게이트/STOVE와 관계가 없습니다.
