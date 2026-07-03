# V10 GitHub Source Findings and Root Cause

Date: 2026-07-03

## Repositories reviewed

- `sagarkerhalkar/SagarSystemHealthMonitor-V10`
- `sagarkerhalkar/Systeam_Monitor_Tool`, branch `master`
- `sagarkerhalkar/Systeam_Monitor_Tool`, branch `universal-server-v8.5`

## Main finding

V10 is not failing because 2278 source data is missing. V10 is failing because the browser runtime loads many patch scripts together. The old V10 UI renderer and the selected-machine renderer overwrite each other.

## Evidence from V10 source

`public/index.html` still loads old and new scripts at the same time:

- `v10_phase3_fix9_global.js`
- `v10_isp_wan_settings_ui.js`
- `v10_home_traffic_kpi.js`
- `v10_hardware_2278_readonly.js`
- `v10_software_2278_readonly.js`
- `v10_bind_2278_clean.js`
- `v10_selected_machine_contract_ui.js`

This creates duplicate state, duplicate renderers, duplicate selected-machine logic, and repeated UI override.

## Evidence from old V8.5 source

The old source already has good logic for:

- Stable machine identity using hostname + physical MAC + valid hardware IDs.
- Filtering fake serials like OEM/default/BSS values.
- Payload summarization into latest table summary JSON.
- CPU, RAM, disk, GPU, USB, software, network, traffic, public IP, ISP, VPN.

## Evidence from V10 work log

V10 already created these milestones today:

- Phase 2 payload normalizer.
- 2278 read-only live source connector.
- Hardware tab read-only 2278 source.
- Software tab read-only 2278 source.
- UI bind to 2278 source.
- No-flicker fix.
- Selected-machine data contract.

But each step added another runtime layer instead of replacing the old runtime.

## Correct fix

Tomorrow, create one clean app runtime:

- `public/v10_clean_app_2278.js`
- `public/v10_clean_app_2278.css`

Then change `public/index.html` so only the clean runtime is loaded for core pages.

Keep old JS files in source for history, but do not load them in the browser.

## Do not repeat

Do not again add another script at the end of index.html. That will repeat the same issue.
