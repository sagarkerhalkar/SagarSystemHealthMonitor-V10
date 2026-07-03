# V10 DEVELOPMENT RULES â€” NO MORE PATCH LOOP

1. Do not replace active frontend without copying old frontend to backup and checking old logic.
2. Do not replace backend without DB migration test.
3. Do not call any build final unless acceptance checklist passes.
4. Do not remove working modules:
   - Machine 360
   - USB/peripherals
   - Inventory Add/Edit/Delete
   - Notifications locked rules
   - Deploy commands
   - Client messages
   - Settings/users/roles/branding/retention
5. Every new requirement must go into docs before coding.
6. Every error must go into error history before/after fixing.
7. Every fix must have a test.
8. Every apply script must call Git autosave if repo exists.
9. Main 2278 must not be touched unless explicitly requested.
10. V10 work must stay on `D:\SagarMonitor_V10_CleanBuild` / port 2294.
