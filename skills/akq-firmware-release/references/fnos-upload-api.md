# fnOS Upload API Notes

## Verified Context

- Verified date: 2026-07-02
- Site: `https://fnos.yuelaniot.com:5667`
- Frontend build date observed in console: 2026-05-07
- Verification method: Playwright login with saved encrypted credential, then dynamic import of `/assets/index-CMZOY5-G.js` inside the page.
- Current Akq team path resolved as:

```text
vol1/@team/阿科奇
```

- Current TW18 LT52 Lezhi release folder path resolved as:

```text
vol1/@team/阿科奇/阿科奇-国内/TW18_阿科奇_LT52_乐智/20260702_1726
```

## Page SDK Entrypoints

After login, import the app bundle in page context:

```js
const mod = await import('/assets/index-CMZOY5-G.js');
const api = mod.d;
```

Useful exports observed:

- `mod.d`: fnOS websocket/RPC API client.
- `mod.aY()`: current fnOS token; used as `Trim-Token`.
- `mod.kA(path)`: HMAC/sign helper; used as `Trim-Sign`.
- `mod.kz`: axios instance used by the frontend for `/upload`.

Useful API groups observed:

- `api.file.ls`
- `api.file.lsDir`
- `api.file.teamLsDir`
- `api.file.mkdir`
- `api.file.checkUpload`
- `api.file.rm`
- `api.mountmgr.acquireUploadCacheDir`
- `api.mountmgr.startUpload`
- `api.mountmgr.cleanUploadCacheDir`

The Akq domestic team-folder upload target is normal team storage, not remote mount storage, so `mountmgr.*Upload*` is not needed for this release path.

## Listing Team Files

Many file list APIs are streaming APIs. Do not rely on plain `await api.file.ls(...)` for file data; it often returns only final `result: "succ"`.

Collect files through `createObservable()`:

```js
function collectFiles(promise) {
  return new Promise((resolve, reject) => {
    const files = [];
    const ob = promise.createObservable();
    ob.subscribe(ev => {
      if (ev.files) files.push(...ev.files);
      if (ev.result && ev.result !== 'doing') {
        ev.result === 'succ' ? resolve(files) : reject(ev);
      }
    });
  });
}
```

Resolve team root folders with:

```js
const teams = await collectFiles(api.file.teamLsDir());
const teamPaths = teams.map(f => `vol${f.v}/@team/${f.name}`);
```

Then list children with:

```js
const children = await collectFiles(api.file.ls({ path }));
```

## Upload Flow

Do not use `api.file.checkUpload` as a harmless existence check. It creates 0-byte placeholder files such as `name.~#0` when called with rename/skip-like strategies. Always list the target folder first and compare names locally.

Safe release upload flow:

1. For compile-before-upload preflight, run `scripts/fnos_upload_release.js --preflight --release-time <YYYYMMDD_HHMM>`. This verifies login, product-folder mapping, timestamp-folder behavior, and same-name remote collisions without requiring local zip/mdb files.
2. Resolve the remote product folder by listing existing folders. Do not create missing team/domestic/product folders.
3. Resolve the release timestamp folder by listing the confirmed product folder. If parent listing misses the folder, directly list the target release path before assuming it is missing.
4. If the remote release timestamp folder does not exist, create only that final `YYYYMMDD_HHMM` folder for a real upload. In dry-run mode, report that it would be created without changing the remote side.
5. List the remote release folder with `api.file.ls({ path: targetDir }).createObservable()`.
6. If any intended upload filename already exists, stop before overwriting. During resume only, `--allow-existing-identical` may skip same-name files whose remote sizes exactly match local sizes.
7. For each file that is definitely going to be uploaded, call:

```js
const targetPath = `${targetDir}/${fileName}`;
const check = await api.file.checkUpload({
  size: fileSize,
  path: targetPath,
  overwrite: 3
});
```

`overwrite: 3` is required to preserve the exact filename. The observed enum is:

```text
Skip=0
Replace=1
Rename=2
Alway=3
```

8. Upload the file with `POST /upload`.

Required multipart form field:

```text
trim-upload-file
```

Required headers:

```text
Trim-Path: encodeURI(uploadPath)
Trim-From: check.from || 0
Trim-Overwrite: 3
Trim-Mtim: floor(localFileMtimeMs / 1000)
Trim-Token: mod.aY()
Trim-Sign: mod.kA(encodeURI(uploadPath))
```

For the normal release flow, `uploadPath` should remain `${targetDir}/${fileName}` because `overwrite: 3` returns the original name. If the response ever returns a different `uploadName`, stop unless the user explicitly accepts the changed remote filename.

9. Verify by listing the target folder again and matching filenames/sizes.
10. On failure after `checkUpload`, clean only Codex-created placeholders with:

```js
await api.file.rm({
  files: [uploadPath, uploadPath.replace(/~#(\d+)$/, '~@$1')],
  moveToTrashbin: false
});
```

## Important Pitfalls

- Hidden `input[type=file]` upload is fragile and can hang. Prefer the page SDK plus `/upload`.
- `checkUpload` can create remote 0-byte placeholder files. Do not probe with production-like names unless you are ready to clean them.
- `overwrite` is not a boolean. Use `3` only after a separate remote-list collision check.
- `readme.txt` follows the release rule: upload only when the user provided exact readme content/file.
