# V10 Phase3 Fix6 UI + Live Requirement Correction

Date: 2026-07-03

## User feedback that caused Fix6
The previous UI still did not match the requirement. Specific issues:

- Machine selector appeared in the top header on every page. Requirement: no global top machine selector; machine selector should appear only inside machine-specific pages.
- Team/person photo appeared as internal page background. Requirement: internal pages should use logo only. Photo should be only for login/background preview with foreground glass effect.
- Color style was confusing and not corporate enough.
- Animation was not useful and looked confusing.
- Inventory editing was not clear. Requirement: visible Edit button per row that loads the form, then Save/Delete.
- Tests must use live server data and not dummy rows.
- GitHub push verification must be available.

## What Fix6 changes
- Replaces internal page hero with clean corporate logo-only hero.
- Removes global top machine selector.
- Adds machine selector only inside Machine 360, Network, Hardware, USB pages.
- Adds clearer hardware/software inventory table actions: Edit and Delete per row.
- Adds CSV export, sample CSV and browser-side import flow.
- Adds API compatibility so hardware inventory endpoint returns both `rows` and `assets` arrays.
- Keeps live data only. Empty API result displays `No rows from live API`, not dummy data.
- Adds/repairs `scripts/CHECK_GITHUB_PUSH_STATUS.ps1`.

## Still to verify with user
- Exact final color preference after seeing Fix6.
- Actual inventory edit/save against live DB.
- Exact live client payload data completeness for disk/GPU/USB/network.
