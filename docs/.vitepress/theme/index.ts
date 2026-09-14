import DefaultTheme from 'vitepress/theme'
import { useLightbox } from './lightbox'
import './custom.css'

/* 主题只做一件事：给相册网格加上"点开看原图"的浮层预览。
 *
 * 相册卡片由 scraper/emit.py 生成，结构是
 *   <a class="photo-preview" href="{原图}" data-caption="…"><img src="{预览图}"></a>
 * 网格里显示 webp 预览图，点开看 jpg 原图（照片没有原图时两者是同一个文件）。
 * 脚本不生效也不影响可用性：链接本身就能在新窗口打开原图。
 *
 * 用 extends 而不是覆盖 enhanceApp —— 默认主题在这里注册了 Badge 组件，
 * VitePress 会把两者的 enhanceApp 串起来（见 vitepress/dist/client/app/index.js）。
 */
export default {
  extends: DefaultTheme,
  enhanceApp() {
    useLightbox()
  },
}
