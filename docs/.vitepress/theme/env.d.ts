/// <reference types="vite/client" />

/* Vite 的类型声明：让 `import './custom.css'` 这类副作用导入有类型可依，
 * 顺便带上 `import.meta.env` 的定义。
 * 少了它，编辑器会把 custom.css 的导入报成"找不到模块"（构建不受影响，
 * 但诊断噪音会盖住真正的错误）。
 */
