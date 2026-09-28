/* Force open tabs onto the new SW after an update activates.
 * Older production builds used injectRegister:'script', which never enabled
 * skipWaiting — deploys sat in "waiting" and users kept stale UI. */
let isUpdate = false

self.addEventListener('install', () => {
  isUpdate = Boolean(self.registration.active)
})

self.addEventListener('activate', (event) => {
  if (!isUpdate) return
  event.waitUntil(
    self.clients.claim().then(() =>
      self.clients.matchAll({ type: 'window' }).then((clients) => {
        for (const client of clients) {
          if ('navigate' in client) {
            client.navigate(client.url)
          }
        }
      })
    )
  )
})
