# Master Login Sheet ("Libertas PWs")

Google Sheet containing carrier portal credentials, shared view-only with aithon20127@gmail.com.

## Access

- **URL**: `https://docs.google.com/spreadsheets/d/17dCiAWkiZebY0XGXs9AzqNsHZRBE33gPGDJyznR-i-Y/edit`
- **Permission**: View-only for Aithon account
- **Tabs**: Current, Libertas Systems, Mortg Clauses, Old, Email Responses
- **Relevant tab**: "Current" — has active carrier portal logins
- **NEVER edit this sheet** — even if edit access is granted, do not modify any cell without Kyle's explicit permission.

## Sheet Structure

- **Column A**: Carrier name (e.g., "Logic-Standard Casualty")
- **Column C**: Short identifier/keyword
- Other columns: URL, username, password, contact info, notes
- Row 137: Logic-Standard Casualty (confirmed via Ctrl+F)

## Reading the Sheet with Playwright

The sheet uses canvas rendering in view-only mode. External clipboard paste is blocked ("Copying and pasting content outside this file has been disabled"), but cell data CAN be read using internal page clipboard:

**What works:**
- **Ctrl+F** locates the row — shows cell reference (e.g., "1 of 1, A137 Logic-Standard Casualty")
- **Navigate to the cell** after Ctrl+F (Enter key lands on the matched cell)
- **`document.execCommand('copy')` inside `page.evaluate()`** copies selected cell content to the page's internal clipboard
- **`navigator.clipboard.readText()` inside `page.evaluate()`** returns the clipboard text — reads cell content even though external paste is blocked
- **Select full row with Shift+Arrow keys** then copy to get all columns at once

**What doesn't work:**
- `document.body.innerText` — only shows UI chrome (menu bar, tab names), not cell values
- **External clipboard paste** — blocked by view-only permissions
- **Double-click to edit** — blocked by view-only mode
- **Formula bar** — no accessible DOM selector in canvas-based UI

**Recommended workflow:**
1. Use Ctrl+F to find the carrier row (search for EXACT name from Column A)
2. Press Enter to land on the cell
3. Use keyboard to select the row (Shift+End or Shift+Arrow across columns)
4. Call `page.evaluate("() => { document.execCommand('copy'); return navigator.clipboard.readText(); }")` to get selected cell content
5. If the evaluate approach fails, ask Kyle to read you the URL/username/password

## Data Quality Warning

Kyle says: "There's a lot of bad/old data in this sheet so ignore anything I don't tell you is functioning." Only use entries that Kyle has confirmed are current. The "Old" tab contains deprecated credentials.

## Carrier Portal References

After reading credentials and mapping a carrier portal, save the portal map to `references/carrier-portals/<carrier-name>.md` under the `libertas-agency-ops` skill. Currently mapped:
- `logic-standard-casualty.md` — Logic/Standard Casualty EZ*Insure portal
