
## 20260703_174048 - Requirement stored
Home page must show Today Download, Today Upload, Current Download, Current Upload from live client traffic. No dummy values.

## 20260703_175628 - Requirement stored
V10 must read 2278 live data in read-only mode first, then test notifications, then proceed to Hardware tab. Do not modify 2278.

## 20260703_180848 - Hardware tab locked implementation path
Hardware tab must read live hardware details from 2278 read-only source first: CPU, RAM, disk, GPU, USB, network, software count, serial/BIOS/motherboard serial when reported. Missing fields must show Not reported by client, not fake values. CSV download required. Notification test must remain working.

