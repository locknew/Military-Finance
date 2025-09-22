export default {
  head: {
    title: 'Payslip Viewer',
    htmlAttrs: { lang: 'en' },
    meta: [
      { charset: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { hid: 'description', name: 'description', content: 'Military Payslip Viewer' },
      { name: 'format-detection', content: 'telephone=no' }
    ],
    link: [
      { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }
    ]
  },

  css: ['@/assets/css/tailwind.css'],

  runtimeConfig: {
    public: {
      liffId: process.env.VITE_LIFF_ID,
      liffRedirectUri: 'https://financepj.netlify.app',
      apiBase: process.env.VITE_API_BASE || 'https://military-finance.onrender.com/api'
    }
  },

  app: {
    baseURL: '/',
    head: [{ title: 'Payslip Viewer' },
      {rel: 'icon', type: 'image/x-icon', href: '/favicon.ico'},

    ]
  },

  plugins: ['~/plugins/liff-init.client.js'],

  components: true,
  buildModules: ['@nuxtjs/eslint-module'],
  build: {},
  nitro: { preset: 'netlify' }
}
