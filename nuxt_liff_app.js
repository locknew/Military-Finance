export default {
  "nuxt-liff-app/": {
    "nuxt.config.ts": `
import { defineNuxtConfig } from 'nuxt/config'

export default defineNuxtConfig({
  css: ['@/assets/css/tailwind.css'],
  modules: [],
  app: {
    head: {
      title: 'Payslip LIFF App'
    }
  }
})`,

    "assets/css/tailwind.css": `
@tailwind base;
@tailwind components;
@tailwind utilities;`,

    "plugins/liff.client.ts": `
import liff from '@line/liff';

export default defineNuxtPlugin(async (nuxtApp) => {
  if (process.client) {
    await liff.init({ liffId: 'YOUR_LIFF_ID' });
    if (!liff.isLoggedIn()) {
      liff.login();
    }
    const profile = await liff.getProfile();
    nuxtApp.provide('lineUser', profile);
  }
});`,

    "utils/isAdmin.ts": `
export const adminList = ['YOUR_ADMIN_LINE_ID_1', 'YOUR_ADMIN_LINE_ID_2'];

export function isAdmin(userId: string): boolean {
  return adminList.includes(userId);
}`,

    "pages/index.vue": `
<template>
  <div class="p-4 max-w-lg mx-auto text-center">
    <h1 class="text-2xl font-bold mb-4">📄 ตรวจสอบสลิปเงินเดือน</h1>
    <form @submit.prevent="fetchSlip">
      <input v-model="account" placeholder="กรอกเลขบัญชี" class="input" />
      <select v-model="month" class="input">
        <option disabled value="">เลือกเดือน</option>
        <option v-for="(num, name) in months" :key="name" :value="num">{{ name }}</option>
      </select>
      <select v-model="year" class="input">
        <option disabled value="">เลือกปี</option>
        <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
      </select>
      <button class="bg-blue-500 text-white px-4 py-2 rounded mt-4" type="submit">ดูสลิป</button>
    </form>
    <div v-if="pdfUrl" class="mt-4">
      <iframe :src="pdfUrl" width="100%" height="500px"></iframe>
      <a :href="pdfUrl" download class="block mt-2 text-blue-600">ดาวน์โหลด PDF</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
const account = ref('');
const month = ref('');
const year = ref('');
const pdfUrl = ref('');
const months = {
  'มกราคม': '01', 'กุมภาพันธ์': '02', 'มีนาคม': '03', 'เมษายน': '04',
  'พฤษภาคม': '05', 'มิถุนายน': '06', 'กรกฎาคม': '07', 'สิงหาคม': '08',
  'กันยายน': '09', 'ตุลาคม': '10', 'พฤศจิกายน': '11', 'ธันวาคม': '12'
};
const years = ['2567', '2568'];

const fetchSlip = async () => {
  const res = await fetch('https://your-backend/api/get-slip', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ account: account.value, month: month.value, year: year.value })
  });
  const data = await res.json();
  if (data.url) pdfUrl.value = data.url;
};
</script>

<style scoped>
.input {
  @apply block w-full p-2 border border-gray-300 rounded mb-2;
}
</style>`,

    "pages/admin.vue": `
<template>
  <div class="p-4 max-w-lg mx-auto text-center">
    <h1 class="text-2xl font-bold mb-4">🧑‍💼 อัปโหลดสลิปใหม่</h1>
    <div v-if="!isAuthorized">ไม่อนุญาตให้เข้าถึง</div>
    <div v-else>
      <input type="file" @change="onFileChange" class="mb-2" />
      <select v-model="month" class="input">
        <option disabled value="">เลือกเดือน</option>
        <option v-for="(num, name) in months" :key="name" :value="num">{{ name }}</option>
      </select>
      <select v-model="year" class="input">
        <option disabled value="">เลือกปี</option>
        <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
      </select>
      <button @click="uploadFile" class="bg-green-600 text-white px-4 py-2 rounded mt-2">อัปโหลด</button>
      <div v-if="uploadStatus" class="mt-2">{{ uploadStatus }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import liff from '@line/liff';
import { isAdmin } from '@/utils/isAdmin';

const month = ref('');
const year = ref('');
const file = ref<File|null>(null);
const uploadStatus = ref('');
const isAuthorized = ref(false);
const months = {
  'มกราคม': '01', 'กุมภาพันธ์': '02', 'มีนาคม': '03', 'เมษายน': '04',
  'พฤษภาคม': '05', 'มิถุนายน': '06', 'กรกฎาคม': '07', 'สิงหาคม': '08',
  'กันยายน': '09', 'ตุลาคม': '10', 'พฤศจิกายน': '11', 'ธันวาคม': '12'
};
const years = ['2567', '2568'];

onMounted(async () => {
  await liff.init({ liffId: 'YOUR_LIFF_ID' });
  const profile = await liff.getProfile();
  isAuthorized.value = isAdmin(profile.userId);
});

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement;
  if (target.files?.length) file.value = target.files[0];
}

async function uploadFile() {
  if (!file.value || !month.value || !year.value) return;

  const form = new FormData();
  form.append('file', file.value);
  form.append('month', month.value);
  form.append('year', year.value);

  const res = await fetch('https://your-backend/api/upload-slip', {
    method: 'POST',
    body: form
  });
  const result = await res.json();
  uploadStatus.value = result.message;
}
</script>

<style scoped>
.input {
  @apply block w-full p-2 border border-gray-300 rounded mb-2;
}
</style>`
  }
}
