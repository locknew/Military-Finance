<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100 p-6">
    <div class="bg-white p-6 rounded-xl shadow-md w-full max-w-md">
      <h2 class="text-lg font-semibold text-center mb-4">
        📄 ตรวจสอบสลิปเงินเดือน
      </h2>

      <input v-model="account" placeholder="เลขบัญชี" class="input mb-3" />

      <div class="grid grid-cols-2 gap-3">
        <select v-model="selectedYear" class="input">
          <option value="">ปี</option>
          <option v-for="y in availableYears" :key="y" :value="y">
            {{ y }}
          </option>
        </select>

        <select v-model="selectedMonth" class="input" :disabled="!selectedYear">
          <option value="">เดือน</option>
          <option v-for="m in availableMonths" :key="m" :value="m">
            {{ m }}
          </option>
        </select>
      </div>

      <button @click="getSlip" class="btn mt-4 w-full">
        📥 แสดงสลิปเงินเดือน
      </button>

      <div v-if="pdfUrl" class="mt-6">
        <iframe :src="pdfUrl" class="w-full h-96 border rounded"></iframe>
      </div>

      <!-- 👮‍♂️ Admin-only: Upload PDF -->
      <div v-if="isAdminUser" class="mt-8 border-t pt-4">
        <h3 class="text-md font-semibold mb-2">👮‍♂️ อัปโหลดไฟล์ PDF (แอดมิน)</h3>
        <input
          type="file"
          accept="application/pdf"
          @change="handleFileUpload"
          class="input"
        />
        <button @click="uploadPDF" class="btn mt-3 w-full">🚀 อัปโหลด</button>
        <p v-if="uploadMessage" class="text-sm mt-2 text-green-600">
          {{ uploadMessage }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import isAdmin from '@/utils/isAdmin';

const { $liff, $liffInit } = useNuxtApp();

const account = ref("");
const availableYears = ref([]);
const availableMonths = ref([]);
const selectedYear = ref("");
const selectedMonth = ref("");
const pdfUrl = ref("");
const file = ref(null);
const uploadMessage = ref("");
const isAdminUser = ref(false);

onMounted(async () => {
  await liff.init({ liffId: import.meta.env.VITE_LIFF_ID })

  if (!$liff.isLoggedIn()) {
    // $liff.login({ redirectUri: window.location.href });
    $liff.login();
    return;
  }

  const profile = await $liff.getProfile();
  if (isAdmin(profile.userId)) {
    isAdminUser.value = true;
  }
  // Fetch dynamic year-month map
  const res = await fetch("locknew.pythonanywhere.com/api/available-months");
  const data = await res.json();
  availableYears.value = Object.keys(data);

  watch(selectedYear, (newYear) => {
    availableMonths.value = data[newYear] || [];
    selectedMonth.value = "";
  });
});

const getSlip = async () => {
  const res = await fetch('locknew.pythonanywhere.com/api/get-slip', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      account: account.value,
      month: selectedMonth.value,
      year: selectedYear.value
    })
  })
  const data = await res.json()
  pdfUrl.value = data.url
};

// Handle PDF file selection
const handleFileUpload = (e) => {
  file.value = e.target.files[0];
};

// Upload selected PDF file to backend
const uploadPDF = async () => {
  if (!file.value) {
    uploadMessage.value = "⚠️ กรุณาเลือกไฟล์ PDF ก่อน";
    return;
  }

  const formData = new FormData();
  formData.append("file", file.value);

  const res = await fetch("locknew.pythonanywhere.com/api/upload-slip", {
    method: "POST",
    body: formData,
  });

  const result = await res.json();
  if (res.ok) {
    uploadMessage.value = "✅ อัปโหลดเรียบร้อยแล้ว!";
  } else {
    uploadMessage.value = `❌ อัปโหลดล้มเหลว: ${
      result.message || "ไม่ทราบสาเหตุ"
    }`;
  }
};
</script>

<style scoped>
.input {
  @apply p-2 border rounded w-full;
}
.btn {
  @apply bg-green-600 text-white font-bold py-2 px-4 rounded hover:bg-green-700;
}
</style>
