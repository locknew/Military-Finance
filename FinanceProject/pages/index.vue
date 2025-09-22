<template>
  <div class="min-h-screen bg-military-gradient flex items-center justify-center p-5">
    <!-- Login Screen -->
    <div v-if="!isLoggedIn" class="login-container fade-in">
      <div class="login-header">
        <div class="login-icon">🪖</div>
        <h1 class="login-title">ระบบสลิปเงินเดือนทหาร</h1>
        <p class="login-subtitle">เข้าสู่ระบบด้วย LINE</p>
      </div>

      <button @click="handleLogin" class="login-btn" :disabled="isLoggingIn">
        <span v-if="isLoggingIn" class="spinner"></span>
        <span v-else>💬</span>
        {{ isLoggingIn ? "กำลังเข้าสู่ระบบ..." : "เข้าสู่ระบบด้วย LINE" }}
      </button>
    </div>

    <!-- Main App -->
    <div v-else class="container fade-in">
      <!-- Header -->
      <div class="header">
        <span class="header-icon">🪖</span>
        <h1 class="header-title">ตรวจสอบสลิปเงินเดือน</h1>
        <p class="header-subtitle">ระบบตรวจสอบสลิปเงินเดือนทหาร</p>
      </div>

      <!-- Search Type -->
      <div class="form-group">
        <label class="form-label">วิธีค้นหา</label>
        <div class="search-type-buttons">
          <button
            v-for="type in ['account','name']"
            :key="type"
            @click="searchType = type"
            :class="['search-type-btn', { active: searchType === type }]"
          >
            <span>{{ type === 'account' ? '🔢' : '👤' }}</span>
            {{ type === 'account' ? 'เลขบัญชี' : 'ชื่อ-นามสกุล' }}
          </button>
        </div>
      </div>

      <!-- Account Input -->
      <div v-if="searchType === 'account'" class="form-group">
        <label class="form-label">เลขบัญชี</label>
        <input v-model="account" placeholder="กรอกเลขบัญชีของคุณ" class="input" />
      </div>

      <!-- Name Input -->
      <div v-if="searchType === 'name'" class="form-group">
        <label class="form-label">ชื่อ-นามสกุล</label>
        <input
          v-model="searchName"
          placeholder="กรอกชื่อหรือนามสกุล"
          class="input"
          @input="handleNameSearch"
        />

        <div v-if="searchResults.length" class="search-results">
          <div class="search-results-header">พบ {{ searchResults.length }} รายการ</div>
          <div
            v-for="result in searchResults"
            :key="result._id"
            @click="selectSearchResult(result)"
            :class="['search-result-item', { selected: selectedResult?._id === result._id }]"
          >
            <div class="result-info">
              <span>{{ result.rank }} {{ result.name }}</span>
              <span>{{ result.accountNumber }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Year / Month Select -->
      <div class="form-group">
        <label class="form-label">เลือกช่วงเวลา</label>
        <div class="grid">
          <select v-model="selectedYear" class="input">
            <option value="">เลือกปี</option>
            <option v-for="y in availableYears" :key="y">{{ y }}</option>
          </select>

          <select v-model="selectedMonth" class="input" :disabled="!selectedYear">
            <option value="">เลือกเดือน</option>
            <option v-for="m in availableMonths" :key="m" :value="m">
              {{ getMonthName(m) }}
            </option>
          </select>
        </div>
      </div>

      <!-- Show Slip -->
      <button @click="getSlip" class="btn" :disabled="loading">
        <span v-if="loading" class="loading"></span>
        <span v-else>📥</span>
        {{ loading ? "กำลังโหลด..." : "แสดงสลิปเงินเดือน" }}
      </button>

      <!-- PDF Viewer -->
      <div v-if="pdfUrl" class="pdf-container slide-up">
        <div class="pdf-header">
          <span v-if="currentSlipInfo.name">{{ currentSlipInfo.rank }} {{ currentSlipInfo.name }}</span>
          <button @click="downloadPdf" class="download-btn">💾 ดาวน์โหลด</button>
        </div>
        <iframe :src="pdfUrl" class="pdf-iframe"></iframe>
      </div>

      <!-- Admin Panel -->
      <div v-if="isAdminUser" class="admin-section slide-up">
        <div class="admin-header">
          <h3>อัปโหลดไฟล์ PDF</h3><span class="admin-badge">ADMIN</span>
        </div>

        <!-- Upload -->
        <div class="form-group">
          <div class="file-input">
            <input id="file-upload" type="file" accept=".pdf" @change="handleFileUpload" ref="fileInput" hidden />
            <label for="file-upload" class="file-input-label">📄 คลิกเพื่อเลือกไฟล์ PDF</label>
          </div>

          <div v-if="selectedFile" class="file-preview">
            <span>{{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})</span>
            <button @click="clearFile" class="clear-btn">✕</button>
          </div>
        </div>

        <button @click="uploadPDF" class="btn" :disabled="uploadLoading || !selectedFile">
          <span v-if="uploadLoading" class="loading"></span>
          <span v-else>🚀</span>
          {{ uploadLoading ? "กำลังอัปโหลด..." : "อัปโหลด" }}
        </button>

        <div v-if="uploadMessage" class="success-message">{{ uploadMessage }}</div>
        <div v-if="uploadError" class="error-message">❌ {{ uploadError }}</div>

        <!-- File list -->
        <div v-if="uploadedFiles.length" class="uploaded-files-section">
          <h4>ไฟล์ที่อัปโหลดแล้ว</h4>
          <div v-for="file in uploadedFiles" :key="file._id" class="file-item">
            <div>
              <span>{{ file.rank }} {{ file.name || file.accountNumber }}</span>
              <span>{{ file.month }}/{{ file.year }}</span>
            </div>
            <div>
              <button @click="viewFile(file)">👁️</button>
              <button @click="deleteFile(file._id)">🗑️</button>
            </div>
          </div>
        </div>
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
const searchType = ref("account");
const account = ref("");
const searchName = ref("");
const searchResults = ref([]);
const selectedResult = ref(null);

const availableYears = ref([]);
const availableMonths = ref([]);
const selectedYear = ref("");
const selectedMonth = ref("");

const pdfUrl = ref("");
const currentSlipInfo = ref({});
const uploadedFiles = ref([]);

const selectedFile = ref(null);
const fileInput = ref(null);

const isAdminUser = ref(false);
const isLoggedIn = ref(false);
const isLoggingIn = ref(false);
const loading = ref(false);
const uploadLoading = ref(false);

const uploadMessage = ref("");
const uploadError = ref("");
const userProfile = ref(null);

// --- Constants ---
const THAI_MONTHS = {
  "01": "มกราคม", "02": "กุมภาพันธ์", "03": "มีนาคม",
  "04": "เมษายน", "05": "พฤษภาคม", "06": "มิถุนายน",
  "07": "กรกฎาคม", "08": "สิงหาคม", "09": "กันยายน",
  "10": "ตุลาคม", "11": "พฤศจิกายน", "12": "ธันวาคม"
};

// --- Utils ---
const getMonthName = (m) => THAI_MONTHS[m] || m;
const formatFileSize = (b) => !b ? "0 Bytes" : 
  (["Bytes","KB","MB","GB"])[Math.floor(Math.log(b)/Math.log(1024))] ?
  `${(b/Math.pow(1024,Math.floor(Math.log(b)/Math.log(1024)))).toFixed(2)} ${["Bytes","KB","MB","GB"][Math.floor(Math.log(b)/Math.log(1024))]}` : "0 Bytes";

// --- Lifecycle ---
onMounted(async () => {
  try {
    await $liff.init({ liffId: config.public.liffId });
    if ($liff.isLoggedIn()) {
      isLoggedIn.value = true;
      userProfile.value = await $liff.getProfile();
      if (isAdmin(userProfile.value.userId)) {
        isAdminUser.value = true;
        await loadUploadedFiles();
      }
      await fetchAvailableMonths();
    }
  } catch (e) {
    console.error("LIFF init failed:", e);
  }
});

// --- Watchers ---
watch(selectedYear, (y) => {
  availableMonths.value = yearMonthData[y] || [];
  selectedMonth.value = "";
});

// --- Data cache ---
let yearMonthData = {};
let searchTimer = null;

// --- API Calls ---
const api = async (url, opts={}) => {
  const res = await fetch(`${API_BASE}${url}`, opts);
  return res.json();
};

const fetchAvailableMonths = async () => {
  try {
    const data = await api("/available-months");
    if (data.success && data.data) {
      yearMonthData = data.data;
      availableYears.value = Object.keys(data.data).sort((a,b)=>b-a);
    }
  } catch (e) {
    console.error("fetchAvailableMonths:", e);
  }
};

const searchByName = async () => {
  try {
    const data = await api("/search", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ search: searchName.value })
    });
    if (data.success) searchResults.value = data.results || [];
  } catch (e) {
    console.error("searchByName:", e);
  }
};

const getSlip = async () => {
  if (!account.value || !selectedYear.value || !selectedMonth.value) {
    alert("กรุณากรอกข้อมูลให้ครบถ้วน"); return;
  }
  loading.value = true; pdfUrl.value = ""; currentSlipInfo.value = {};
  try {
    const data = await api("/get-slip", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account: account.value, year: selectedYear.value, month: selectedMonth.value })
    });
    if (data.success) {
      pdfUrl.value = data.pdfData;
      currentSlipInfo.value = data.metadata || {};
    } else throw new Error(data.error);
  } catch (e) { alert(e.message || "โหลดสลิปผิดพลาด"); }
  finally { loading.value = false; }
};

// --- Handlers ---
const handleLogin = () => { isLoggingIn.value = true; $liff.login(); };

const handleNameSearch = () => {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    searchName.value.length >= 2 ? searchByName() : searchResults.value = [];
  }, 500);
};

const selectSearchResult = (r) => {
  selectedResult.value = r; account.value = r.accountNumber; selectedYear.value = r.year;
  setTimeout(()=> selectedMonth.value = r.month, 100);
};

const downloadPdf = () => {
  if (!pdfUrl.value) return;
  const a = document.createElement("a");
  a.href = pdfUrl.value;
  a.download = `slip_${account.value}_${selectedMonth.value}_${selectedYear.value}.pdf`;
  a.click();
};

const handleFileUpload = (e) => {
  const f = e.target.files[0];
  if (!f) return;
  if (f.type !== "application/pdf") return uploadError.value = "เลือก PDF เท่านั้น";
  if (f.size > 10*1024*1024) return uploadError.value = "ไฟล์เกิน 10MB";
  selectedFile.value = f; uploadError.value = ""; uploadMessage.value = "";
};

const clearFile = () => {
  selectedFile.value = null; uploadMessage.value = ""; uploadError.value = "";
  if (fileInput.value) fileInput.value.value = "";
};

const uploadPDF = async () => {
  if (!selectedFile.value) return uploadError.value = "กรุณาเลือกไฟล์";
  uploadLoading.value = true; uploadMessage.value = ""; uploadError.value = "";
  try {
    const form = new FormData(); form.append("file", selectedFile.value);
    const res = await fetch(`${API_BASE}/upload-slip`, { method:"POST", body:form });
    const data = await res.json();
    if (res.ok && data.success) {
      uploadMessage.value = data.message || "อัปโหลดสำเร็จ!";
      await loadUploadedFiles(); await fetchAvailableMonths(); clearFile();
    } else throw new Error(data.error);
  } catch (e) { uploadError.value = e.message; }
  finally { uploadLoading.value = false; }
};

const loadUploadedFiles = async () => {
  try {
    const data = await api("/files/list?limit=20");
    if (data.success) uploadedFiles.value = data.files || [];
  } catch (e) { console.error("loadUploadedFiles:", e); }
};

const deleteFile = async (id) => {
  if (!confirm("คุณแน่ใจว่าจะลบ?")) return;
  try {
    const data = await api(`/files/delete?file_id=${id}`, { method:"DELETE" });
    if (data.success) uploadedFiles.value = uploadedFiles.value.filter(f=>f._id!==id);
  } catch (e) { uploadError.value = e.message; }
};

const viewFile = async (file) => {
  loading.value = true;
  try {
    const data = await api("/get-slip", {
      method: "POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ account:file.accountNumber, year:file.year, month:file.month })
    });
    if (data.success) {
      pdfUrl.value = data.pdfData; currentSlipInfo.value = data.metadata || {};
      account.value = file.accountNumber; selectedYear.value = file.year; selectedMonth.value = file.month;
    }
  } catch (e) { alert("ดูไฟล์ผิดพลาด"); }
  finally { loading.value = false; }
};
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