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

      <!-- Name Input + Search -->
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
            <span class="result-date">{{ result.month }}/{{ result.year }}</span>
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
        
        <!-- Mobile: Use object tag for better compatibility -->
        <div v-if="isMobile" class="pdf-mobile-container">
          <object :data="pdfUrl" type="application/pdf" class="pdf-object">
            <div class="pdf-fallback">
              <p>ไม่สามารถแสดง PDF ได้บนอุปกรณ์นี้</p>
              <button @click="openPdfNewTab" class="btn-open-pdf">เปิดในหน้าต่างใหม่</button>
              <button @click="downloadPdf" class="btn-download-pdf">ดาวน์โหลด PDF</button>
            </div>
          </object>
        </div>
        
        <!-- Desktop: Use iframe -->
        <iframe v-else :src="pdfUrl" class="pdf-iframe"></iframe>
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

// Detect mobile device
const isMobile = ref(false);

// --- Constants ---
const THAI_MONTHS = {
  "01": "มกราคม", "02": "กุมภาพันธ์", "03": "มีนาคม",
  "04": "เมษายน", "05": "พฤษภาคม", "06": "มิถุนายน",
  "07": "กรกฎาคม", "08": "สิงหาคม", "09": "กันยายน",
  "10": "ตุลาคม", "11": "พฤศจิกายน", "12": "ธันวาคม"
};

// --- Utils ---
const getMonthName = (m) => THAI_MONTHS[m] || m;
const formatFileSize = (b) => {
  if (!b) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return `${(b / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
};

// --- Lifecycle ---
onMounted(async () => {
  // Detect mobile
  isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  
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
      // Convert base64 to data URL
      pdfUrl.value = `data:application/pdf;base64,${data.pdfBase64}`;
      currentSlipInfo.value = data.metadata || {};
    } else throw new Error(data.error);
  } catch (e) { 
    alert(e.message || "โหลดสลิปผิดพลาด"); 
  }
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
  
  if ($liff.isInClient()) {
    // If in LINE app, construct backend download URL and open in external browser
    const downloadUrl = `${API_BASE}/download-pdf?account=${account.value}&year=${selectedYear.value}&month=${selectedMonth.value}`;
    
    $liff.openWindow({
      url: downloadUrl,
      external: true
    });
  } else {
    // Fallback for web browser - trigger normal download using data URL
    const a = document.createElement("a");
    a.href = pdfUrl.value;
    a.download = `slip_${account.value}_${selectedMonth.value}_${selectedYear.value}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
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
    if (data.success) {
      uploadedFiles.value = uploadedFiles.value.filter(f=>f._id!==id);
      uploadMessage.value = "ลบไฟล์สำเร็จ";
    }
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
      pdfUrl.value = `data:application/pdf;base64,${data.pdfBase64}`;
      currentSlipInfo.value = data.metadata || {};
      account.value = file.accountNumber; selectedYear.value = file.year; selectedMonth.value = file.month;
      
      // Scroll to PDF viewer
      setTimeout(() => {
        document.querySelector('.pdf-container')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  } catch (e) { alert("ดูไฟล์ผิดพลาด"); }
  finally { loading.value = false; }
};
</script>

<style scoped>
@import url('@/assets/css/tailwind.css');
</style>
