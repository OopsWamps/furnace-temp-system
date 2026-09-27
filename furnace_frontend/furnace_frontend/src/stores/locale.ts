import { defineStore } from 'pinia'
import { ref } from 'vue'
import { messages, localeNames, type Locale } from '@/utils/i18n'

const STORAGE_KEY = 'furnace_locale'

function getSavedLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && Object.keys(localeNames).includes(saved)) {
    return saved as Locale
  }
  return 'zh-hans'
}

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref<Locale>(getSavedLocale())

  function t(key: string): string {
    return messages[locale.value][key] || key
  }

  function setLocale(l: Locale) {
    locale.value = l
    localStorage.setItem(STORAGE_KEY, l)
    document.documentElement.lang = l
  }

  // Set initial lang
  document.documentElement.lang = locale.value

  return { locale, t, setLocale }
})