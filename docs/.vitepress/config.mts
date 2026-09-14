import { defineConfig } from 'vitepress'
import { sidebar } from './sidebar.generated.mts'

export default defineConfig({
  lang: 'zh-CN',
  title: '兔子山的小站',
  description:
    '《轻音！》系列、《玉子市场》、《玉子爱情故事》、《聲之形》… 世界中闪耀的光辉☆ 山田尚子作品专题站',

  // 站点由 scraper 归档生成，正文里大量使用单换行表示折行。
  // 开启 breaks 才能忠实还原豆瓣原文的 <br> 语义（见 scraper/html2md.py）。
  markdown: {
    breaks: true,
    lineNumbers: false,
    image: { lazyLoading: true },
  },

  // 关键：把死链检查交给构建流程。任何指向不存在的 md / 图片都会让构建失败，
  // 这样 scraper verify 之外还有第二道防线。
  ignoreDeadLinks: false,
  cleanUrls: true,
  lastUpdated: true,
  metaChunk: true,

  head: [
    ['meta', { name: 'theme-color', content: '#f7b8c4' }],
    ['meta', { property: 'og:type', content: 'website' }],
  ],

  themeConfig: {
    logo: '/media/site/avatar.jpg',
    siteTitle: '兔子山的小站',

    nav: [
      { text: '首页', link: '/' },
      { text: '文章索引', link: '/notes/' },
      { text: '相册', link: '/albums/' },
      { text: '视频', link: '/videos' },
      { text: '留言板', link: '/board' },
      { text: '关于', link: '/about' },
    ],

    sidebar,

    outline: { level: [2, 3], label: '本页目录' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    lastUpdated: { text: '最后更新于' },

    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索文档', buttonAriaLabel: '搜索文档' },
          modal: {
            displayDetails: '显示详情',
            resetButtonTitle: '清除查询条件',
            noResultsText: '没有找到相关结果',
            footer: {
              selectText: '选择',
              navigateText: '切换',
              closeText: '关闭',
            },
          },
        },
        // 中文正文按空格分词效果差，改用逐字切分提升召回
        miniSearch: {
          options: {
            tokenize: (text: string) => text.split(/[\s\-_,，。、；：！？（）《》“”‘’]+/u).filter(Boolean),
          },
        },
      },
    },

    socialLinks: [{ icon: 'github', link: 'https://site.douban.com/211330/' }],

    footer: {
      message: '本站为原豆瓣小站的本地归档，内容版权归原作者所有',
      copyright: '原站由 羽音 于 2013-05-01 创建',
    },

    darkModeSwitchLabel: '主题',
    lightModeSwitchTitle: '切换到浅色模式',
    darkModeSwitchTitle: '切换到深色模式',
    sidebarMenuLabel: '目录',
    returnToTopLabel: '回到顶部',
    externalLinkIcon: true,
  },
})
