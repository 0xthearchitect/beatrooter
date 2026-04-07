# BeatNote — Implementation Plan

## 1) Goal
Implement BeatNote as a lightweight note system for beat production workflows, integrated with existing popup infrastructure.

## 2) Scope (MVP)
- Create/Edit/Delete notes
- List notes in reserved BeatNote area
- Search and filter notes
- Persist notes locally (v1)
- Basic UX polish (shortcuts, unsaved-change warning, toasts)

## 3) Data Model
```ts
type BeatNoteCategory =
  | "idea"
  | "drums"
  | "melody"
  | "bass"
  | "mix"
  | "master"
  | "reference"
  | "todo"
  | "other";

interface BeatNote {
  id: string; // uuid
  title: string; // required, max 120
  content: string; // max 5000
  category: BeatNoteCategory;
  tags: string[];
  pinned: boolean;
  createdAt: string; // ISO
  updatedAt: string; // ISO
}
```

## 4) Persistence Strategy (v1)
- Storage key: `beatrooter.beatnotes.v1`
- Local-first service abstraction:
  - `list()`
  - `create(input)`
  - `update(id, patch)`
  - `delete(id)`

Implementation note:
- In the current PyQt desktop app, local persistence is backed by `QSettings` under the same versioned key. This keeps the storage abstraction local-first while matching the existing application architecture.

## 5) UX Rules
- Popup modal reused from existing system
- Auto-focus title on open
- Save shortcut: Ctrl/Cmd + Enter
- Confirm before delete
- Warn on close with unsaved changes
- Toast feedback on success/error

## 6) Sorting/Filtering
- Default order:
  - `pinned = true` first
  - `updatedAt desc`
- Filters:
  - `category`
  - `pinned only`
- Search:
  - `title + content` partial match

## 7) Issue Breakdown & Dependencies
### BN-01 Define domain model and validation rules
Depends on: none

Done when:
- BeatNote type and validation rules approved.

Out of scope:
- Backend sync
- Rich text/markdown editing

### BN-02 Build BeatNote persistence service (local-first)
Depends on: BN-01

Done when:
- CRUD works and persists after refresh.

Out of scope:
- Remote sync
- Conflict resolution

### BN-03 Render BeatNote panel (list + empty state)
Depends on: BN-02

Done when:
- Notes visible in reserved UI area.

Out of scope:
- Advanced analytics
- Multi-column board views

### BN-04 Implement BeatNote modal (create/edit)
Depends on: BN-01, BN-02, BN-03

Done when:
- Modal supports create/edit with full form.

Out of scope:
- Attachment uploads
- Markdown preview

### BN-05 Integrate full CRUD flow + delete confirmation
Depends on: BN-04

Done when:
- Full lifecycle works from UI.

Out of scope:
- Version history
- Bulk actions

### BN-06 Add search, filters, and ordering
Depends on: BN-05

Done when:
- Combined filter/search behavior works.

Out of scope:
- Saved views
- Complex boolean filtering

### BN-07 UX polish (shortcut, unsaved warning, toasts)
Depends on: BN-05

Done when:
- Interaction quality baseline met.

Out of scope:
- Notifications outside the BeatNote workspace
- Multi-user awareness

### BN-08 Add tests (service + UI integration)
Depends on: BN-02, BN-05, BN-06, BN-07

Done when:
- Test suite passes in CI.

Out of scope:
- End-to-end browser tests
- Visual regression tooling

### BN-09 Final documentation
Depends on: all

Done when:
- Feature usage and architecture documented.

Out of scope:
- Product marketing copy
- Long-form tutorials

## 8) Acceptance Criteria
- User can create/edit/delete BeatNotes via modal.
- Data survives refresh.
- Search and filters behave correctly.
- Pinned notes appear first.
- No regressions in popup system.
- Core tests pass.

## 9) Risks & Mitigations
- Risk: popup state conflicts with existing modals
  - Mitigation: isolate BeatNote modal state and keep close guards inside the dialog.
- Risk: local storage schema changes
  - Mitigation: versioned key and service boundary for future migration.
- Risk: filtering complexity
  - Mitigation: pure selector functions plus unit tests.

## 10) Future Enhancements (post-MVP)
- API sync (cloud persistence)
- Markdown support
- Note version history
- Export/import JSON

## 11) Current Feature Map
- Welcome entry point: `BeatRooter/ui/welcome_window.py`
- Dedicated BeatNote window: `BeatRooter/ui/beatnote_main_window.py`
- BeatNote domain rules: `BeatRooter/core/beatnote_model.py`
- BeatNote persistence service: `BeatRooter/core/beatnote_service.py`
- BeatNote modal: `BeatRooter/ui/beatnote_dialog.py`
- BeatNote panel/list UI: `BeatRooter/ui/beatnote_panel.py`
- Tests: `tests/projects/beatnote/test_beatnote_service.py` and `tests/projects/beatnote/test_beatnote_ui.py`

## 12) Backend Migration Path
- Replace the internals of `BeatNoteService` with an API-backed implementation that preserves the same public methods.
- Keep the `BeatNote` validation and selector logic unchanged so UI code remains stable.
- Add a repository adapter layer for:
  - `GET /beatnotes`
  - `POST /beatnotes`
  - `PUT /beatnotes/:id`
  - `DELETE /beatnotes/:id`
- Migrate local notes by reading the versioned `QSettings` payload once and posting it to the backend on first sync.
