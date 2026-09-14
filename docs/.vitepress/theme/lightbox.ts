/* 相册放大预览（原图查看）
 *
 * 相册网格里显示的是**预览图**（源站详情页那张，几十到几百 KB），
 * 点开之后看的应该是**原图**（"查看原图"链接指向的 raw 文件，常有数 MB）。
 * 这个脚本把网格里的 `<a class="photo-preview">` 接管成站内浮层预览：
 *
 *   - 先立刻显示已经加载过的预览图，再在后台加载原图、就绪后替换
 *     （原图大，直接等它会让点击长时间没反应）；
 *   - Esc / 点背景 / 点关闭按钮退出，← → 在同一相册内翻页；
 *   - 按住 Cmd/Ctrl/Shift 点击、或用中键点击时不接管，
 *     浏览器照旧在新窗口打开原图（脚本没生效时也是这个行为）。
 *
 * 刻意不引入任何依赖，也不改动 VitePress 的主题结构：
 * 事件委托挂在 document 上，因此 SPA 路由切换后无需重新绑定。
 * 详见 scraper/emit.py 的 emit_album()。
 */

const ROOT_CLASS = 'usagi-lightbox'
const OPEN_CLASS = 'usagi-lightbox-open'

let installed = false
let overlay: HTMLElement | null = null
let viewer: HTMLImageElement | null = null
let captionBox: HTMLElement | null = null
let openLink: HTMLAnchorElement | null = null
let statusBox: HTMLElement | null = null
/** 当前相册内的全部可预览链接，用于 ← → 翻页 */
let gallery: HTMLAnchorElement[] = []
let index = -1
/** 加载序号：原图是异步替换的，翻页后旧图的回调必须作废 */
let token = 0

export function useLightbox(): void {
  if (typeof document === 'undefined' || installed) return
  installed = true

  document.addEventListener('click', onClick)
  document.addEventListener('keydown', onKeydown)
}

function previewsIn(link: Element): HTMLAnchorElement[] {
  const grid = link.closest('.photo-grid')
  const scope: ParentNode = grid ?? document
  return Array.from(scope.querySelectorAll<HTMLAnchorElement>('a.photo-preview'))
}

function onClick(event: MouseEvent): void {
  if (event.defaultPrevented || event.button !== 0) return
  // 让"在新窗口打开"这类原生行为照常工作
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return

  const target = event.target as Element | null
  const link = target?.closest?.('a.photo-preview') as HTMLAnchorElement | null
  if (!link) return

  const href = link.getAttribute('href')
  if (!href) return

  event.preventDefault()
  gallery = previewsIn(link)
  open(gallery.indexOf(link) >= 0 ? gallery.indexOf(link) : 0)
}

function onKeydown(event: KeyboardEvent): void {
  if (!overlay || overlay.hidden) return
  if (event.key === 'Escape') {
    close()
  } else if (event.key === 'ArrowLeft') {
    step(-1)
  } else if (event.key === 'ArrowRight') {
    step(1)
  }
}

function build(): void {
  overlay = document.createElement('div')
  overlay.className = ROOT_CLASS
  overlay.hidden = true
  overlay.setAttribute('role', 'dialog')
  overlay.setAttribute('aria-modal', 'true')
  overlay.setAttribute('aria-label', '原图预览')
  // 点背景关闭；点在图或控件上时不关
  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) close()
  })

  const figure = document.createElement('figure')
  viewer = document.createElement('img')
  viewer.className = 'lb-image'
  viewer.alt = ''
  viewer.decoding = 'async'

  const bar = document.createElement('figcaption')
  bar.className = 'lb-bar'
  captionBox = document.createElement('span')
  captionBox.className = 'lb-caption'
  statusBox = document.createElement('span')
  statusBox.className = 'lb-status'
  openLink = document.createElement('a')
  openLink.className = 'lb-open'
  openLink.target = '_blank'
  openLink.rel = 'noopener'
  openLink.textContent = '新窗口打开'
  bar.append(captionBox, statusBox, openLink)

  figure.append(viewer, bar)
  overlay.append(figure, button('lb-close', '关闭', '×'), button('lb-prev', '上一张', '‹'), button('lb-next', '下一张', '›'))
  document.body.append(overlay)

  overlay.querySelector('.lb-close')?.addEventListener('click', close)
  overlay.querySelector('.lb-prev')?.addEventListener('click', () => step(-1))
  overlay.querySelector('.lb-next')?.addEventListener('click', () => step(1))
}

function button(className: string, label: string, text: string): HTMLButtonElement {
  const node = document.createElement('button')
  node.type = 'button'
  node.className = className
  node.setAttribute('aria-label', label)
  node.textContent = text
  return node
}

function open(at: number): void {
  if (!overlay) build()
  if (!overlay) return

  const wasHidden = overlay.hidden
  if (wasHidden) {
    overlay.hidden = false
    document.body.classList.add(OPEN_CLASS)
  }
  show(at)
  if (wasHidden) overlay.querySelector<HTMLButtonElement>('.lb-close')?.focus()
}

function show(at: number): void {
  const link = gallery[at]
  if (!overlay || !viewer || !captionBox || !openLink || !statusBox || !link) return
  index = at

  const thumb = link.querySelector('img')
  const src = link.getAttribute('href') || thumb?.getAttribute('src') || ''
  // 已经加载过的预览图先顶上，避免等原图时一片空白
  const placeholder = thumb?.currentSrc || thumb?.getAttribute('src') || src
  const caption = link.dataset.caption || ''

  token += 1
  const current = token
  viewer.src = placeholder
  viewer.classList.toggle('is-loading', placeholder !== src)
  captionBox.textContent = caption
  captionBox.hidden = !caption
  openLink.href = src
  openLink.textContent = placeholder === src ? '新窗口打开' : '新窗口打开原图'
  statusBox.textContent = placeholder === src ? '' : '正在载入原图…'

  const prev = overlay.querySelector<HTMLElement>('.lb-prev')
  const next = overlay.querySelector<HTMLElement>('.lb-next')
  if (prev) prev.hidden = gallery.length < 2
  if (next) next.hidden = gallery.length < 2

  if (placeholder === src) return

  // 原图往往有好几 MB：后台加载完再替换，加载失败就留在预览图上
  const big = new Image()
  big.decoding = 'async'
  big.onload = () => {
    if (current !== token || !viewer || !statusBox) return // 已经翻页或关掉了
    viewer.src = src
    viewer.classList.remove('is-loading')
    statusBox.textContent = ''
  }
  big.onerror = () => {
    if (current !== token || !viewer || !statusBox) return
    viewer.classList.remove('is-loading')
    statusBox.textContent = '原图加载失败，当前为预览图'
  }
  big.src = src
}

function step(delta: number): void {
  if (gallery.length < 2) return
  show((index + delta + gallery.length) % gallery.length)
}

function close(): void {
  if (!overlay || overlay.hidden) return
  overlay.hidden = true
  document.body.classList.remove(OPEN_CLASS)
  token += 1 // 作废在途的原图加载
  if (viewer) viewer.removeAttribute('src')
  gallery = []
  index = -1
}
