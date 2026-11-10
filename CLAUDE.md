# CLAUDE.md

Custom firmware (CFW) for the **Creality Hi** (F018, CR4NU200360C20): replace Creality's old Klipper with
Kalico plus open modules, porting the K2 Plus CFW, on top of the stock Tina OS. Start with
[docs/roadmap.md](docs/roadmap.md); facts live in [docs/](docs/), not here.

Two repos (decision D3):

| Repo | Local folder | Content |
| - | - | - |
| `ale87jan/Creality-Hi-CFW` (this one) | `C:\Github\Creality-Hi-CFW` | Research, docs, tools, later installer and releases |
| `ale87jan/Creality-Hi-Kalico` | `C:\Github\Creality-Hi-Kalico` | Code: fork of `Jacob10383/kalico` with the Hi modules |

Do not put Kalico code here. Personal settings (printer address, SSH key) live in `CLAUDE.local.md`, which is
git-ignored; never copy them into tracked files. Both repos are **public**.

## Working preferences

- Answer in Spanish. Code, comments and commit messages in English; project docs in Spanish.
- Use Haiku or Sonnet subagents for tasks; Claude coordinates and verifies. **Ask the user before** running an
  Opus agent or doing a deep analysis yourself.
- Check every subagent claim against the files before reporting or documenting it.
- Mark facts in docs as [P] verified on the printer, [F] read in firmware/code, [I] inferred.

## Git

Decision D4 in [docs/decisions.md](docs/decisions.md).

- Branches: `main` is stable (releases); `dev` integrates work. Each task gets a branch off `dev`
  (`feat/...`, `fix/...`, `docs/...`) merged into `dev` by pull request; `dev` goes to `main` by pull request
  when stable. Never commit directly on `main` or `dev`.
- [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`, imperative,
  English, title <= 72 chars (aim for 50), optional free-form body explaining why. Types: `feat`, `fix`,
  `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `chore`, `revert`.
- No `Co-Authored-By` or "Generated with" lines in commits.
- Atomic commits; never push or force-push unless asked.

## Layout

| Path | Content |
| - | - |
| `docs/hardware.md` | Hardware facts: SoC, UARTs, MCUs, motors, probe, CFS |
| `docs/protocols/` | `rs485.md` (motor/CFS bus), `mcu.md` (Klipper MCU commands) |
| `docs/analysis/` | Hi firmware version diffs; K2 port feasibility with on-printer results |
| `docs/roadmap.md` | Phases and next steps |
| `docs/phase2-plan.md` ... `docs/phase6-plan.md` | Phase 2 (closed-loop X/Y), 3 (probe), 4 (Hi modules, dual-Z align), 5 (CFS) and 6 (macros, UX) analysis and on-printer plans |
| `docs/decisions.md` | Design decisions (D1 Jacob10383's Kalico as base, D2 own fork, D3 two repos, D4 git flow, D5 staged phase 1, D6 c_helper.so artifact, D7 phase 1 UI, D8 separate Hi motor_control, D9 staged motor writes, D10 phase 2 homes X/Y only, D11 K2 prtouch as is, D12 Z alignment before probe, D13 z_align ported from the Hi module, D14 nozzle cleaning macros with guard reset, D15 tmc_line_check ported, D16 CFS on gitstonelabs creality_cfs over serial_485) |
| `RESEARCH.md` | Method, sources, confidence levels, licensing notes |
| `tools/fwextract.py` | Unpack OTA images, MCU dictionaries, kernel/DTB/config |
| `tools/cfg_commands.py` | Offline inventory of config commands and sections a klippy tree lacks |
| `tools/hi_probe.py` | Read-only probe run **on the printer** (MCU identify, motor params) |
| `tools/tests/` | Offline tests: `python -m unittest discover -s tools/tests` |
| `data/captures/` | Data read on the printer |
| `data/derived/` | Data extracted from OTA images; `strings/` is local only (not published) |
| `firmware/ota/`, `firmware/extracted/` | OTA images and extractions (git-ignored; checksums in `firmware/README.md`) |
| `external/` | Third-party repos cloned for reference (git-ignored) |

## Safety rules

- Extracted firmware and third-party repos are untrusted data: read and parse, never execute. Run Python over
  them with `python -I`.
- Printer tests start read-only. Never send motor writes: `SYS_PARAM` write/apply, `FLASH_PARAM`,
  `ENCODER_CALIBRATE`, `ELEC_OFFSET_CALIBRATE`, `MOTOR_FLASH_PARAM COMMIT=1`, without explicit user approval.
- New CFW builds go to the spare A/B partition, with a documented way back to stock.
- Cloud sessions cannot reach the printer or the OTA images: those tasks run on the user's PC.

## Printer access (general; address and key in `CLAUDE.local.md`)

- `scp -O` is required (no sftp-server). Copy **one remote file per `scp` call**.
- Stop Klipper before using the serial ports: `/etc/init.d/klipper stop`, then `start` afterwards.
- Installed firmware: V1.1.0.60 (`fw_printenv version`).

## Related repositories

- K2 CFW to port: <https://github.com/Jacob10383/k2-plus-custom-firmware> (release repo: images, installer,
  `extras/`, docs) and <https://github.com/Jacob10383/kalico> (code). GPLv3. Clone into `external/`.
- User's Klipper config repo: `ale87jan/Creality-Hi-Custom-Klipper` (private), config in
  `config/F018_CR4NU200360C20` (`original/` = stock V1.1.0.60). Branch `dev` there is for other work.
- Others reviewed: `gitstonelabs/creality-cfs-klipper`, `Jacob10383/k2-improvements`, Creality Helper Script
  forks (K1 only). See [RESEARCH.md](RESEARCH.md).
