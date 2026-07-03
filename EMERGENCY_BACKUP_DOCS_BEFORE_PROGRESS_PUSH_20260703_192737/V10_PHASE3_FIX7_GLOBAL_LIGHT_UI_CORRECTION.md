# V10 Phase3 Fix7 - Global Light Corporate UI Correction

Date: 2026-07-03

## Why this fix exists
The user rejected Fix6 because the UI was still too dark, confusing, not global/corporate enough, and some required controls disappeared when other controls were added.

## User complaints locked
- Theme is too dark and not global/customer-friendly.
- UI is confusing; a normal user cannot understand the app flow.
- When asset edit option appears, notification active/off/locked edit option must not disappear.
- Settings page must include organization branding, retention, users, roles and password reset.
- Live data must be used only. No dummy data.
- Inventory edit must be obvious: Edit button per row, form below, Save/Clear.
- GitHub status verification must remain available.

## Fix7 changes
- Replaces dark theme with light global corporate theme.
- Keeps sidebar professional navy but all working pages are light/white cards.
- Keeps internal pages logo-only; no person photo on internal pages.
- Keeps login/team photo only in Settings preview/login background requirement.
- Adds explanatory sections on Home so users understand what the app shows.
- Keeps machine selector only inside machine-specific tabs.
- Keeps Hardware Asset Register row Edit/Delete and import/export/sample CSV.
- Adds Notification Rules active/off/locked controls with Save button for allowed rules.
- Adds Settings user/role/password reset UI blocks.
- Keeps corporate footer on every page.
- Continues live API only; unavailable data is shown as Not reported.

## Next acceptance check
- Home should look light, clear and customer-friendly.
- Notification page must show active/off/locked action controls.
- Hardware inventory must show Edit/Delete per row.
- Settings must include branding, retention, user creation, role and password reset.
- GitHub push check script must exist.
