import liff from '@line/liff'

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()
  const liffId = config.public.liffId

  const initResult = liff.init({ liffId })
    .then(() => {
      console.log('✅ LIFF init succeeded.')
    })
    .catch((error) => {
      console.error('❌ LIFF init failed.', error)
    })

  return {
    provide: {
      liff,
      liffInit: initResult
    }
  }
})
