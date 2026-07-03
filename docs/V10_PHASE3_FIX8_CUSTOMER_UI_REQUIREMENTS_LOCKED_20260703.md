# V10 Phase3 Fix8 Customer UI Requirements Locked

Date: 2026-07-03

## Why this fix exists
User rejected Fix7 because it still did not meet the locked customer requirements:
- GitHub status button must not show to customer.
- Logo color must not be changed; logo must be visible on every page.
- Internal pages should show only logo, not owner/team photo or big organization details.
- Settings should allow upload image files and editable organization name, not folder-path-only settings.
- Router/ISP data must come from router/WAN/Cloudflare/router check configuration, not from client laptop payload.
- Notifications must keep Active/Off/Locked editing controls.
- User creation and password reset UI/API must exist.
- Home page must clearly show live server data and actions.
- UI must look global/corporate, not local-shop/dark/confusing.
- ISO Audit must be audit-style: missing serial/vendor/invoice, unmatched asset/machine evidence, and download. Passing an external ISO audit depends on real supporting records being complete; the app must not fake compliance.

## Customer UI rule
- Customer screen must not show GitHub option.
- GitHub status is for developer/server PowerShell only through `scripts/CHECK_GITHUB_PUSH_STATUS.ps1`.
- Logo appears in sidebar, page header and hero.
- Login/team photo is kept only for login background preview in Settings.
- No dummy data. Missing live values show `Not reported`.

## Router ISP rule
- ISP/WAN information is maintained in `router_isp_links` database table.
- Network + VPN page has Add/Edit Router ISP form.
- Home page reads router ISP rows from `/api/v10final/router/isps`.
- This prevents wrong client payload from being presented as router ISP truth.

## Settings rule
Settings must show:
- Organization name.
- Website.
- App title.
- Upload Logo button.
- Upload Login Background button.
- Retention days.
- User / Role Management.
- Roles: Viewer, Asset Entry User, Organization Admin, Super Admin only for Sagar.
- Create/update user.
- Password reset.

## Notification rule
- CPU-only and RAM-only remain locked disabled.
- Admin/Super Admin may switch allowed rules Active/Off and edit threshold.
- Locked rules cannot be edited by normal UI.

## ISO rule
- ISO Audit page must be audit-style and evidence-based.
- It must show total assets, missing serial, missing vendor, missing invoice/PO, unmatched live machine, unmatched assets/machines where data exists.
- It must provide CSV download for evidence.
- It must not claim external certification pass if source data is incomplete.
