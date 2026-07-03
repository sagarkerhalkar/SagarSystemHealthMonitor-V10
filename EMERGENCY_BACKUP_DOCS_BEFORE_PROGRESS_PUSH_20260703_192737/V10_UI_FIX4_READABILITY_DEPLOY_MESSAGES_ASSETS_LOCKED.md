# V10 UI Fix4 Locked Feedback - 20260702_191609

User feedback locked into source:
- Login page font must be fully visible; improve readability and animation without breaking current working UI.
- Deploy page did not visually change; create a real Deploy Command Center with V10 port, firewall, server start, one-client test command, installer/ISO/download evidence.
- Client Messages UI was not good; make target/title/message/priority form readable and sent history clear.
- Uploaded asset details must be visible. Copy uploaded inventory JSON/CSV from data folder to public/generated and show hardware/software asset register with vendor, make, model, serial, warranty, invoice/PO, assigned to, location, status, remarks.
- Notification page should keep backend rules but clearly show active/off/locked status.
- Actual working data must be visible; client payload variants like software.apps and hardware.ram must be handled in UI.
- This patch is UI/source only for V10 2294. It does not touch main 2278 and does not modify notification backend.