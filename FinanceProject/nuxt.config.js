export default {
  // Global page headers
  head: {
    title: 'LIFF App',
    htmlAttrs: { lang: 'en' },
    meta: [
      { charset: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { hid: 'description', name: 'description', content: '' },
      { name: 'format-detection', content: 'telephone=no' }
    ],
    link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }]
  },

  // Global CSS
  css: ['@/assets/css/tailwind.css'],

  // Runtime config for frontend
  runtimeConfig: {
    public: {
      liffId: process.env.VITE_LIFF_ID,
      liffRedirectUri: 'https://financepj.netlify.app',
      apiBase: process.env.VITE_API_BASE || 'https://military-finance.onrender.com/api',
    }
  },

  app: {
    head: { title: 'Payslip Viewer' },
    baseURL: '/',  // required for SPA routing on Netlify
  },

  plugins: ['~/plugins/liff-init.client.js'],

  components: true,

  buildModules: ['@nuxtjs/eslint-module'],

  modules: [],

  build: {},

  // Nitro preset for Netlify
  nitro: { preset: 'netlify' },

  // Ensure SPA fallback on Netlify
  router: {
    options: {
      history: 'hash' // optional: avoids 404s for client-side routes
    }
  }
}
