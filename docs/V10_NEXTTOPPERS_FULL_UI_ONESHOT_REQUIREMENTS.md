# V10 Next Toppers Full UI One-Shot Requirements

This one-shot UI rebuild is locked for V10 on port 2294 only. Main 2278 must not be touched.

## Branding
- Company name: Next Toppers.
- Company website: https://www.nexttoppers.com/
- Login and dashboard must use Next Toppers logo and company photo.
- Settings page must allow company name, website, logo, login photo, and login tagline changes.

## Responsive UI
- Optimized for mobile, tablet, iPad, Apple devices, laptop, desktop and all modern browsers.
- Classic, international SaaS UI: clean typography, premium colors, animation and 3D cards without oversized sections.

## Pages
- Command Center: fleet overview, H/W and S/W overview, ISP health, upload/download, latency, jitter, packet loss, alert overview and change overview.
- Machine Fleet: current machines list. Clicking any machine opens Machine 360.
- Machine 360: simple readable machine details for 5 to 90 year age group: H/W, S/W, CPU, GPU, RAM, HDD/SSD, USB, network, VPN, CSV/PDF export.
- Network + VPN: machine-wise IP, MAC, adapter, public IP and VPN.
- Hardware Intelligence: machine-wise hardware with serial/vendor/warranty/invoice sync fields.
- Software Intelligence: machine-wise software with register sync.
- Hardware Asset Register: international name, not local wording.
- Software Asset Register: clean register with export.
- ISO Audit Center: ISO-style audit evidence and separate H/W/S/W downloads.
- USB + Peripherals: understandable human view.
- Human Change Log: machine-wise and day-wise important changes, especially IP, USB, VPN, hardware and software.
- Day History: fast daily summary without heartbeat samples.
- Client Messages: send message and see sent history.
- Notifications: show backend active alerts and active rules.
- Deploy: deploy/download evidence.
- Settings: user/role management, branding, website, logo, login photo, self password and system settings.

## Roles
- Viewer: read-only live data.
- Inventory Editor: reserved role for inventory edit workflow.
- Admin: user/settings management.
- Super Admin: user/settings management.

## Tests
- Static UI branding/responsive test.
- Static security test: no insecure non-local http references.
