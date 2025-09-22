<template>
  <div class="min-h-screen bg-military-gradient flex flex-col items-center justify-center p-5">

    <!-- Login Screen -->
    <div v-if="!isLoggedIn" class="login-container fade-in">
      <div class="login-header text-center">
        <div class="login-icon text-4xl">🪖</div>
        <h1 class="login-title text-2xl font-bold mt-2">ระบบสลิปเงินเดือนทหาร</h1>
        <p class="login-subtitle mt-1">เข้าสู่ระบบด้วย LINE</p>
      </div>

      <button @click="handleLogin" class="login-btn mt-4" :disabled="isLoggingIn">
        <span v-if="isLoggingIn" class="spinner"></span>
        <span v-else>💬</span>
        {{ isLoggingIn ? "กำลังเข้าสู่ระบบ..." : "เข้าสู่ระบบด้วย LINE" }}
      </button>
    </div>

    <!-- Main App -->
    <div v-else class="w-full max-w-4xl fade-in">
      <!-- Header -->
      <div class="header text-center mb-6">
        <span class="header-icon text-3xl">🪖</span>
        <h1 class="header-title text-xl font-bold mt-2">ตรวจสอบสลิปเงินเดือน</h1>
        <p class="header-subtitle text-sm mt-1">ระบบตรวจสอบสลิปเงินเดือนทหาร</p>
      </div>

      <!-- Account & Period Selection -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <input v-model="account" placeholder="เลขบัญชี" class="input p-2 border rounded" />
        <select v-model="selectedYear" class="input p-2 border rounded">
          <option value="">เลือกปี</option>
          <option v-for="y in availableYears" :key="y">{{ y }}</option>
        </select>
        <select v-model="selectedMonth" class="input p-2 border rounded" :disabled="!selectedYear">
          <option value="">เลือกเดือน</option>
          <option v-for="m in availableMonths" :key="m" :value="m">{{ getMonthName(m) }}</option>
        </select>
      </div>

      <!-- Show Slip Button -->
      <button @click="getSlip" class="btn mb-4" :disabled="loading">
        <span v-if="loading" class="loading"></span>
        <span v-else>📥</span>
        {{ loading ? "กำลังโหลด..." : "แสดงสลิปเงินเดือน" }}
      </button>

      <!-- PDF Viewer -->
      <div v-if="pdfUrl" class="pdf-container border p-2 rounded mb-4">
        <div class="flex justify-between items-center mb-2">
          <span v-if="currentSlipInfo.name">{{ currentSlipInfo.rank }} {{ currentSlipInfo.name }}</span>
          <button @click="downloadPdf" class="btn-download">💾 ดาวน์โหลด</button>
        </div>

        <canvas ref="pdfCanvas" class="w-full border"></canvas>
        <div v-if="totalPages > 1" class="flex justify-center items-center mt-2 gap-2">
          <button @click="previousPage" :disabled="currentPage <= 1" class="nav-btn">◀️</button>
          <span>หน้า {{ currentPage }} / {{ totalPages }}</span>
          <button @click="nextPage" :disabled="currentPage >= totalPages" class="nav-btn">▶️</button>
        </div>
        <div v-if="pdfLoading" class="text-center mt-2">
          <div class="spinner mx-auto"></div>
          <p>กำลังโหลด PDF...</p>
        </div>
      </div>

      <!-- Admin Panel -->
      <div v-if="isAdminUser" class="admin-section border p-4 rounded mt-6">
        <h3 class="font-bold mb-2">อัปโหลดไฟล์ PDF <span class="text-red-500 ml-2">ADMIN</span></h3>
        <div class="mb-2">
          <input type="file" accept=".pdf" @change="handleFileUpload" ref="fileInput" />
          <span v-if="selectedFile">{{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})</span>
          <button v-if="selectedFile" @click="clearFile">✕</button>
        </div>
        <button @click="uploadPDF" :disabled="!selectedFile || uploadLoading" class="btn mb-2">
          {{ uploadLoading ? "กำลังอัปโหลด..." : "🚀 อัปโหลด" }}
        </button>
        <div v-if="uploadMessage" class="text-green-600">{{ uploadMessage }}</div>
        <div v-if="uploadError" class="text-red-600">❌ {{ uploadError }}</div>

        <h3 class="font-bold mt-4 mb-2">ลบสลิปเงินเดือน</h3>
        <div class="grid grid-cols-2 gap-2 mb-2">
          <select v-model="deleteYear" class="input p-2 border rounded">
            <option value="">เลือกปี</option>
            <option v-for="y in availableYears" :key="y">{{ y }}</option>
          </select>
          <select v-model="deleteMonth" class="input p-2 border rounded" :disabled="!deleteYear">
            <option value="">ทั้งหมด</option>
            <option v-for="m in getMonthsForYear(deleteYear)" :key="m" :value="m">{{ getMonthName(m) }}</option>
          </select>
        </div>
        <button @click="deleteSlipsByPeriod" :disabled="!deleteYear || deleteLoading" class="btn-delete">
          {{ deleteLoading ? "กำลังลบ..." : deleteMonth ? `ลบสลิปเดือน ${getMonthName(deleteMonth)} ${deleteYear}` : `ลบสลิปทั้งปี ${deleteYear}` }}
        </button>
        <div v-if="deleteMessage" class="text-green-600 mt-1">{{ deleteMessage }}</div>
        <div v-if="deleteError" class="text-red-600 mt-1">❌ {{ deleteError }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { isAdmin } from "@/utils/isAdmin";

const { $liff } = useNuxtApp();
const config = useRuntimeConfig();
const API_BASE = config.public.apiBase;

// --- State ---
const account = ref("");
const availableYears = ref([]);
const availableMonths = ref([]);
const selectedYear = ref("");
const selectedMonth = ref("");
const pdfUrl = ref(""); // Blob URL
const currentSlipInfo = ref({});
const pdfCanvas = ref(null);
const currentPage = ref(1);
const totalPages = ref(0);
const pdfLoading = ref(false);
let pdfDoc = null;

// Admin / Auth state
const isAdminUser = ref(false);
const isLoggedIn = ref(false);
const isLoggingIn = ref(false);
const loading = ref(false);

// Upload / Delete state
const selectedFile = ref(null);
const fileInput = ref(null);
const uploadLoading = ref(false);
const uploadMessage = ref("");
const uploadError = ref("");
const deleteYear = ref("");
const deleteMonth = ref("");
const deleteLoading = ref(false);
const deleteMessage = ref("");
const deleteError = ref("");

// --- Month Utils ---
const THAI_MONTHS = { "01":"มกราคม","02":"กุมภาพันธ์","03":"มีนาคม","04":"เมษายน","05":"พฤษภาคม","06":"มิถุนายน","07":"กรกฎาคม","08":"สิงหาคม","09":"กันยายน","10":"ตุลาคม","11":"พฤศจิกายน","12":"ธันวาคม" };
const getMonthName = m => THAI_MONTHS[m] || m;
let yearMonthData = {};
const getMonthsForYear = (year) => yearMonthData[year] || [];

// --- Lifecycle ---
onMounted(async () => {
  // Load PDF.js
  if (typeof window !== "undefined") {
    const script = document.createElement("script");
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
    script.async = true;
    document.head.appendChild(script);
    script.onload = () => window.pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
  }

  // LIFF login
  try {
    await $liff.init({ liffId: config.public.liffId });
    if ($liff.isLoggedIn()) {
      isLoggedIn.value = true;
      const profile = await $liff.getProfile();
      if (isAdmin(profile.userId)) isAdminUser.value = true;
      await fetchAvailableMonths();
    }
  } catch (e) { console.error("LIFF init failed:", e); }
});

// --- Watchers ---
watch(selectedYear, (y) => { availableMonths.value = yearMonthData[y] || []; selectedMonth.value = ""; });

// --- API ---
const fetchAvailableMonths = async () => {
  try {
    const res = await fetch(`${API_BASE}/available-months`);
    const data = await res.json();
    if (data.success && data.data) {
      yearMonthData = data.data;
      availableYears.value = Object.keys(data.data).sort((a,b)=>b-a);
    }
  } catch(e){ console.error(e); }
};

// --- Get Slip ---
const getSlip = async () => {
  if (!account.value || !selectedYear.value || !selectedMonth.value) { alert("กรุณากรอกข้อมูลให้ครบ"); return; }
  loading.value = true;
  pdfUrl.value = ""; currentSlipInfo.value = {};
  try {
    const res = await fetch(`${API_BASE}/get-slip`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ account: account.value, year: selectedYear.value, month: selectedMonth.value })
    });
    if (!res.ok) throw new Error("ไม่พบไฟล์สลิป");
    const blob = await res.blob();
    pdfUrl.value = URL.createObjectURL(blob);
    await renderPDF(pdfUrl.value);
  } catch(e){ alert(e.message || "โหลดสลิปผิดพลาด"); }
  finally{ loading.value = false; }
};

// --- PDF.js ---
const renderPDF = async (url) => {
  if (!window.pdfjsLib || !pdfCanvas.value) return;
  pdfLoading.value = true;
  try {
    pdfDoc = await window.pdfjsLib.getDocument(url).promise;
    totalPages.value = pdfDoc.numPages; currentPage.value = 1;
    await renderPage(1);
  } catch(e){ console.error(e); alert("โหลด PDF ผิดพลาด"); }
  finally{ pdfLoading.value = false; }
};

const renderPage = async (num) => {
  if (!pdfDoc || !pdfCanvas.value) return;
  const page = await pdfDoc.getPage(num);
  const canvas = pdfCanvas.value;
  const context = canvas.getContext("2d");
  const containerWidth = canvas.parentElement.clientWidth - 20;
  const scale = containerWidth / page.getViewport({ scale: 1 }).width;
  const viewport = page.getViewport({ scale });
  canvas.width = viewport.width; canvas.height = viewport.height;
  await page.render({ canvasContext: context, viewport }).promise;
};

const nextPage = async () => { if(currentPage.value<totalPages.value){ currentPage.value++; await renderPage(currentPage.value); } };
const previousPage = async () => { if(currentPage.value>1){ currentPage.value--; await renderPage(currentPage.value); } };

// --- Download PDF ---
const downloadPdf = () => {
  if(!pdfUrl.value) return;
  const a = document.createElement("a");
  a.href = pdfUrl.value;
  a.download = `slip_${account.value}_${selectedMonth.value}_${selectedYear.value}.pdf`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
};

// --- File Upload ---
const handleFileUpload = (e) => { selectedFile.value = e.target.files[0]; };
const clearFile = () => { selectedFile.value = null; fileInput.value.value = null; };
const uploadPDF = async () => { /* implement upload logic */ };

// --- Delete ---
const deleteSlipsByPeriod = async () => { /* implement delete logic */ };

// --- LIFF Login ---
const handleLogin = () => { isLoggingIn.value = true; $liff.login(); };
</script>




<style>

.bg-military-gradient {
  background: linear-gradient(
    135deg,
    #2d5016 0%,
    #3e6b2b 25%,
    #4a7c3a 50%,
    #5a8b4a 75%,
    #6aa85a 100%
  );
}

.login-container {
  max-width: 400px;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 40px 32px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  text-align: center;
}

.login-header {
  margin-bottom: 32px;
}

.login-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 8px;
}

.login-subtitle {
  color: #718096;
  font-size: 16px;
  margin-bottom: 32px;
}

.login-btn {
  width: 100%;
  padding: 16px;
  background: #06c755;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.download-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.pdf-iframe {
  width: 100%;
  height: 400px;
  border: none;
}

/* PDF Viewer Container */
.pdf-viewer-container {
  position: relative;
  background: #f7fafc;
  padding: 20px;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.pdf-canvas {
  max-width: 100%;
  height: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  background: white;
}

.pdf-navigation {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  padding: 12px 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.nav-btn {
  background: linear-gradient(135deg, #3e6b2b 0%, #4a7c3a 100%);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.nav-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(74, 124, 58, 0.3);
}

.nav-btn:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
  opacity: 0.5;
}

.page-info {
  font-weight: 600;
  color: #2d3748;
  font-size: 14px;
}

.pdf-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #4a5568;
}

.pdf-loading .spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top-color: #4a7c3a;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 12px;
}

.pdf-loading p {
  margin: 0;
  font-size: 14px;
}

/* Mobile PDF View */
.mobile-pdf-view {
  padding: 40px 20px;
  text-align: center;
  background: #f7fafc;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.mobile-pdf-icon {
  font-size: 64px;
  margin-bottom: 8px;
}

.mobile-pdf-text {
  color: #4a5568;
  font-size: 16px;
  line-height: 1.6;
  margin-bottom: 8px;
}

.mobile-view-btn {
  background: linear-gradient(135deg, #3e6b2b 0%, #4a7c3a 50%, #5a8b4a 100%);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 14px 28px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-view-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(74, 124, 58, 0.3);
}

.mobile-view-btn:active {
  transform: translateY(0);
}

/* Admin Section */
.admin-section {
  margin-top: 32px;
  padding-top: 32px;
  border-top: 2px solid #e2e8f0;
}

.admin-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.admin-title {
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
}

.admin-badge {
  background: linear-gradient(135deg, #2d5016 0%, #4a7c3a 100%);
  color: white;
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.file-input {
  position: relative;
  overflow: hidden;
  display: inline-block;
  width: 100%;
}

.file-input input[type="file"] {
  position: absolute;
  left: -9999px;
}

.file-input-label {
  display: block;
  width: 100%;
  padding: 16px;
  background: #f7fafc;
  border: 2px dashed #cbd5e0;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #718096;
}

.file-input-label:hover {
  background: #edf2f7;
  border-color: #a0aec0;
}

.file-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f7fafc;
  padding: 12px;
  border-radius: 8px;
  margin-top: 8px;
  border: 1px solid #e2e8f0;
}

.file-info {
  display: flex;
  flex-direction: column;
}

.file-name {
  font-weight: 500;
  color: #2d3748;
  font-size: 14px;
}

.file-size {
  color: #718096;
  font-size: 12px;
  margin-top: 2px;
}

.clear-btn {
  background: #fc8181;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.clear-btn:hover {
  background: #f56565;
}

/* Uploaded Files Section */
.uploaded-files-section {
  margin-top: 24px;
  padding: 16px;
  background: #f7fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.files-title {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 12px;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.file-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.file-actions {
  display: flex;
  gap: 8px;
}

.view-btn, .delete-btn {
  padding: 6px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 16px;
}

.view-btn {
  background: #4299e1;
  color: white;
}

.view-btn:hover {
  background: #3182ce;
}

.delete-btn {
  background: #fc8181;
  color: white;
}

.delete-btn:hover {
  background: #f56565;
}

.success-message {
  background: #c6f6d5;
  color: #22543d;
  padding: 12px;
  border-radius: 8px;
  margin-top: 16px;
  font-size: 14px;
  text-align: center;
}

.error-message {
  background: #fed7d7;
  color: #742a2a;
  padding: 12px;
  border-radius: 8px;
  margin-top: 16px;
  font-size: 14px;
  text-align: center;
}

/* Delete Section */
.delete-section {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #e2e8f0;
}

.btn-delete {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #c53030 0%, #e53e3e 50%, #fc8181 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-delete:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(197, 48, 48, 0.3);
}

.btn-delete:active {
  transform: translateY(0);
}

.btn-delete:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
  transform: none;
}

/* Responsive Design for Mobile */
@media (max-width: 640px) {
  .container {
    padding: 24px 20px;
    margin: 10px;
  }

  .header-icon {
    font-size: 40px;
  }

  .header-title {
    font-size: 20px;
  }

  .grid {
    grid-template-columns: 1fr;
  }

  .pdf-iframe {
    height: 300px;
  }

  .mobile-pdf-view {
    padding: 30px 16px;
    min-height: 250px;
  }

  .mobile-pdf-icon {
    font-size: 48px;
  }

  .mobile-pdf-text {
    font-size: 14px;
  }
}

.fade-in {
  animation: fadeIn 0.5s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.slide-up {
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Custom scrollbar for search results */
.search-results::-webkit-scrollbar {
  width: 6px;
}

.search-results::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.search-results::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 3px;
}

.search-results::-webkit-scrollbar-thumb:hover {
  background: #a0aec0;
}

.hidden {
  display: none;
}
.login-btn:hover {
  background: #05b04d;
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(6, 199, 85, 0.3);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #ffffff;
  border-top: 2px solid transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.container {
  max-width: 480px;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 32px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header-icon {
  font-size: 48px;
  margin-bottom: 16px;
  display: block;
}

.header-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 8px;
}

.header-subtitle {
  color: #718096;
  font-size: 14px;
}

/* Search Type Selector */
.search-type-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 8px;
}

.search-type-btn {
  padding: 12px;
  background: #f7fafc;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #718096;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.search-type-btn:hover {
  background: #edf2f7;
  border-color: #cbd5e0;
}

.search-type-btn.active {
  background: linear-gradient(135deg, #3e6b2b 0%, #4a7c3a 50%, #5a8b4a 100%);
  color: white;
  border-color: transparent;
}

/* Search Results */
.search-results {
  background: #f7fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-top: 12px;
  max-height: 200px;
  overflow-y: auto;
}

.search-results-header {
  padding: 8px 12px;
  background: #edf2f7;
  font-size: 12px;
  color: #718096;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
}

.search-result-item {
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-result-item:hover {
  background: #edf2f7;
}

.search-result-item.selected {
  background: #c6f6d5;
}

.search-result-item:last-child {
  border-bottom: none;
}

.result-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.result-name {
  font-weight: 500;
  color: #2d3748;
  font-size: 14px;
}

.result-account {
  font-size: 12px;
  color: #718096;
}

.result-date {
  font-size: 12px;
  color: #a0aec0;
}

.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 8px;
  font-size: 14px;
}

.input {
  width: 100%;
  padding: 16px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  font-size: 16px;
  transition: all 0.3s ease;
  background: white;
  color: #2d3748;
}

.input:focus {
  outline: none;
  border-color: #4a7c3a;
  box-shadow: 0 0 0 3px rgba(74, 124, 58, 0.15);
  transform: translateY(-2px);
}

.input:disabled {
  background: #f7fafc;
  color: #a0aec0;
  cursor: not-allowed;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.btn {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #3e6b2b 0%, #4a7c3a 50%, #5a8b4a 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(74, 124, 58, 0.3);
}

.btn:active {
  transform: translateY(0);
}

.btn:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
  transform: none;
}

.loading {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid #ffffff;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 1s ease-in-out infinite;
}

/* PDF Container */
.pdf-container {
  margin-top: 32px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.pdf-header {
  background: linear-gradient(135deg, #2d5016 0%, #4a7c3a 100%);
  color: white;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.download-btn {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 14px;
  cursor:
}

</style>