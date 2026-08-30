# Retrieving live apps + versions from the App Store and Google Play

Researched 2026-08-30. Applies to any Apple and Google publisher account with
many published apps. Read-only; nothing here writes to a store.

**Summary:** both stores can do it. Apple = 2 calls per app, one API.
Google = no "list my apps" in the publishing API; the list comes from a
*second* API (Play Developer Reporting) and the versions from the first.

---

## Apple — App Store Connect API

Base: `https://api.appstoreconnect.apple.com`

| Need | Call |
|---|---|
| All apps in the team | `GET /v1/apps` → name, bundleId, id |
| Versions of one app | `GET /v1/apps/{id}/appStoreVersions` → `versionString`, state |

The live version is the one whose state is `READY_FOR_DISTRIBUTION`.
`appStoreState`/`READY_FOR_SALE` is the deprecated pre-3.3 spelling of the same
thing and still appears in responses — **accept either** when filtering.
`GET /v1/apps?include=appStoreVersions` folds both calls into one request.

`createdDate` on a version is when it was created in App Store Connect
("Prepare for Submission"), **not** its release date. There is no plain
release-date attribute.

### Credentials
App Store Connect → *Users and Access → Integrations → App Store Connect API*.
Produces an **Issuer ID**, a **Key ID** and a **`.p8` private key file
downloadable exactly once**. A read-only role suffices. Each request carries a
short-lived ES256 JWT signed with the `.p8`.

### Credential-free shortcut
`https://itunes.apple.com/lookup?bundleId=<id>` returns the live version with no
auth at all (this is what in-app "update available?" checks use). One bundle id
per call, and it cannot enumerate — you must already know the list.

---

## Google Play — two APIs, stitched

### 1. The list — Play Developer Reporting API
`GET https://playdeveloperreporting.googleapis.com/v1beta1/apps:search`
Returns every app the caller can access (package name + display name), paginated
via `pageSize`/`pageToken`. Scope
`https://www.googleapis.com/auth/playdeveloperreporting`.

This is the only official way to enumerate a Play account's apps. The publishing
API below has **no** list method — it only answers about a package name you
already supply. That is why the answer to this question used to be "not
possible".

### 2. The versions — Google Play Developer API (androidpublisher v3)
Per package: open an edit → `GET edits.tracks.get(packageName, editId,
track="production")` → read `releases[]`, take the one with
`status: "completed"`. Never commit the edit; abandoning it changes nothing.
Three calls per app.

`versionCodes` (integers) are reliable. The release `name` is only a real version
string if release names are set explicitly — otherwise Google generates it from
the APK's versionName or from the date.

### Credentials
Google Cloud project → enable **both** APIs → service account + JSON key →
**invite that service account into the Play Console and grant it app access**.
The key alone grants nothing; the Play Console invitation is the step people miss.

### No credential-free shortcut
Google has no public lookup equivalent to iTunes Lookup. Scraping the store page
is the only alternative and is fragile.

---

## Gotchas that affect any script built on this

- **"Live" is not a single value on Apple.** Per-territory availability; an app
  can be removed from sale and still carry a live version record.
- **Staged rollouts on Google.** A release at 20% leaves two version codes active
  in production. The script must decide which one it calls "live".
- **Two version identities on Google** (code vs name) — see above.
- **Rate limits.** Apple throttles hourly; Google's edit-per-app pattern is ~3
  calls × N games. Fine for a daily run, not for a polling loop.
- **Nothing links an iOS app to its Android twin.** Matching is manual, usually
  by bundle id / package name convention.

---

## Open thread (not built)

If the project already ships a per-build manifest recording the app version and
both the Android and iOS bundle ids, joining it against the live store versions
answers a more useful question than a plain listing: **which published apps are
running an outdated build of the shared code.** Discussed 2026-08-30, no
decision taken, nothing implemented.

---

## Sources

- https://developer.apple.com/documentation/appstoreconnectapi
- https://developer.apple.com/documentation/appstoreconnectapi/appstoreversionstate
- https://developer.apple.com/documentation/appstoreconnectapi/appversionstate
- https://developers.google.com/play/developer/reporting/reference/rest/v1beta1/apps/search
- https://developers.google.com/play/developer/reporting/overview
- https://developers.google.com/android-publisher/api-ref/rest/v3/edits.tracks
- https://developers.google.com/android-publisher/tracks
