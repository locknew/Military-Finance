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

      <!-- Account Input (Name search removed) -->
      <div class="form-group">
        <label class="form-label">เลขบัญชี</label>
        <input v-model="account" placeholder="กรอกเลขบัญชีของคุณ" class="input" />
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
          <!-- Download button only visible on mobile -->
          <button v-if="isMobile" @click="downloadPdf" class="download-btn">💾 ดาวน์โหลด</button>
        </div>
        
        <!-- Iframe only visible on desktop -->
        <iframe v-if="!isMobile" :src="pdfUrl" class="pdf-iframe"></iframe>
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
          <h4 class="files-title">ไฟล์ที่อัปโหลดแล้ว</h4>
          <div class="files-list">
            <div v-for="file in uploadedFiles" :key="file._id" class="file-item">
              <div class="file-details">
                <div class="file-name">{{ file.rank }} {{ file.name || file.accountNumber }}</div>
                <div class="file-size">{{ file.month }}/{{ file.year }}</div>
              </div>
              <div class="file-actions">
                <button @click="viewFile(file)" class="view-btn" title="ดูไฟล์">👁️</button>
                <button @click="deleteFile(file._id)" class="delete-btn" title="ลบไฟล์">🗑️</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Delete Section for Month/Year -->
        <div class="delete-section">
          <div class="admin-header">
            <h3 class="admin-title">ลบสลิปทั้งเดือน</h3>
            <span class="admin-badge">⚠️ DANGER</span>
          </div>
          
          <div class="form-group">
            <label class="form-label">เลือกเดือน/ปีที่ต้องการลบ</label>
            <div class="grid">
              <select v-model="deleteYear" class="input">
                <option value="">เลือกปี</option>
                <option v-for="y in availableYears" :key="y">{{ y }}</option>
              </select>

              <select v-model="deleteMonth" class="input" :disabled="!deleteYear">
                <option value="">เลือกเดือน</option>
                <option v-for="m in getDeleteMonths()" :key="m" :value="m">
                  {{ getMonthName(m) }}
                </option>
              </select>
            </div>
          </div>

          <div v-if="deleteYear && deleteMonth" class="form-group">
            <div class="success-message" style="background: #fff3cd; color: #856404; border: 1px solid #ffeaa7;">
              ⚠️ คุณกำลังจะลบสลิปทั้งหมดของเดือน {{ getMonthName(deleteMonth) }} พ.ศ. {{ deleteYear }}
              <br><strong>จำนวน: {{ deleteSlipCount }} รายการ</strong>
            </div>
          </div>

          <button 
            @click="deleteMonthSlips" 
            class="btn-delete" 
            :disabled="deleteLoading || !deleteYear || !deleteMonth"
          >
            <span v-if="deleteLoading" class="loading"></span>
            <span v-else>🗑️</span>
            {{ deleteLoading ? "กำลังลบ..." : "ลบสลิปทั้งเดือน" }}
          </button>

          <div v-if="deleteMessage" class="success-message">{{ deleteMessage }}</div>
          <div v-if="deleteError" class="error-message">❌ {{ deleteError }}</div>
        </div>

<!-- Admin Management Section -->
<div class="admin-section slide-up" style="margin-top: 32px; padding-top: 24px; border-top: 2px solid #e2e8f0;">
  <div class="admin-header">
    <h3 class="admin-title">จัดการ Admin</h3>
    <span class="admin-badge">👥 USERS</span>
  </div>

  <!-- Current User Email -->
  <div class="form-group">
    <div class="success-message" style="background: #e6fffa; color: #234e52; border: 1px solid #81e6d9;">
      👤 คุณเข้าสู่ระบบด้วย: <strong>{{ userEmail }}</strong>
    </div>
  </div>

  <!-- Add New Admin -->
  <div class="form-group">
    <label class="form-label">เพิ่ม Admin ใหม่</label>
    <input 
      v-model="newAdminEmail" 
      type="email"
      placeholder="กรอกอีเมลของ Admin ใหม่" 
      class="input"
      @keyup.enter="addAdmin"
    />
  </div>

  <button 
    @click="addAdmin" 
    class="btn" 
    :disabled="adminManageLoading || !newAdminEmail"
    style="background: linear-gradient(135deg, #2b6cb0 0%, #3182ce 50%, #4299e1 100%);"
  >
    <span v-if="adminManageLoading" class="loading"></span>
    <span v-else>➕</span>
    {{ adminManageLoading ? "กำลังเพิ่ม..." : "เพิ่ม Admin" }}
  </button>

  <!-- Admin List -->
  <div v-if="adminEmails.length" class="uploaded-files-section" style="margin-top: 24px;">
    <h4 class="files-title">รายชื่อ Admin ทั้งหมด ({{ adminEmails.length }})</h4>
    <div class="files-list">
      <div v-for="admin in adminEmails" :key="admin.email" class="file-item">
        <div class="file-details">
          <div class="file-name">
            {{ admin.email }}
            <span v-if="admin.email === userEmail" style="color: #48bb78; font-weight: 600;"> (คุณ)</span>
          </div>
          <div class="file-size" v-if="admin.addedAt">
            เพิ่มเมื่อ: {{ new Date(admin.addedAt).toLocaleDateString('th-TH') }}
          </div>
        </div>
        <div class="file-actions">
          <button 
            @click="removeAdmin(admin.email)" 
            class="delete-btn" 
            :disabled="admin.email === userEmail"
            :title="admin.email === userEmail ? 'ไม่สามารถลบตัวเองได้' : 'ลบ Admin'"
          >
            🗑️
          </button>
        </div>
      </div>
    </div>
  </div>

  <div v-if="adminManageMessage" class="success-message" style="margin-top: 16px;">
    {{ adminManageMessage }}
  </div>
  <div v-if="adminManageError" class="error-message" style="margin-top: 16px;">
    ❌ {{ adminManageError }}
  </div>
</div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";

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

// Delete state
const deleteYear = ref("");
const deleteMonth = ref("");
const deleteLoading = ref(false);
const deleteMessage = ref("");
const deleteError = ref("");
const deleteSlipCount = ref(0);

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

const userEmail = ref("");
const adminEmails = ref([]);
const newAdminEmail = ref("");
const adminManageLoading = ref(false);
const adminManageMessage = ref("");
const adminManageError = ref("");

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

const getDeleteMonths = () => {
  return deleteYear.value ? (yearMonthData[deleteYear.value] || []) : [];
};

const fetchDeleteSlipCount = async () => {
  if (!deleteYear.value || !deleteMonth.value) {
    deleteSlipCount.value = 0;
    return;
  }
  
  try {
    const data = await api(`/files/count?year=${deleteYear.value}&month=${deleteMonth.value}`);
    if (data.success) {
      deleteSlipCount.value = data.count;
    }
  } catch (e) {
    console.error("fetchDeleteSlipCount:", e);
    deleteSlipCount.value = 0;
  }
};
// Helper function to decode JWT
const decodeJWT = (token) => {
  try {
    // Get the payload part (second part of JWT)
    const base64Url = token.split('.')[1];
    
    // Replace URL-safe characters
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    
    // Decode base64 to string
    const jsonPayload = decodeURIComponent(
      window.atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error("JWT decode error:", error);
    return null;
  }
};

// ... rest of your state variables

// Then in onMounted, use it like this:
onMounted(async () => {
  isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  
  try {
    await $liff.init({ liffId: config.public.liffId });
    if ($liff.isLoggedIn()) {
      isLoggedIn.value = true;
      userProfile.value = await $liff.getProfile();
      
      // Get ID token and decode to get email
      const idToken = $liff.getIDToken();
      if (idToken) {
        const payload = decodeJWT(idToken);
        
        if (payload && payload.email) {
          userEmail.value = payload.email;
          console.log("User email:", userEmail.value);
          
          // Check if user is admin using email
          await checkAdminStatus();
        } else {
          console.warn("No email found in token");
        }
      } else {
        console.warn("No ID token available");
      }
      
      await fetchAvailableMonths();
    }
  } catch (e) {
    console.error("LIFF init failed:", e);
  }
});

// New function to check admin status
const checkAdminStatus = async () => {
  try {
    const data = await api("/admin/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: userEmail.value })
    });
    
    if (data.success && data.isAdmin) {
      isAdminUser.value = true;
      await loadUploadedFiles();
      await loadAdminList();
    }
  } catch (e) {
    console.error("checkAdminStatus:", e);
  }
};

// New function to load admin list
const loadAdminList = async () => {
  try {
    const data = await api("/admin/list");
    if (data.success) {
      adminEmails.value = data.admins || [];
    }
  } catch (e) {
    console.error("loadAdminList:", e);
  }
};

// --- Watchers ---
watch(selectedYear, (y) => {
  availableMonths.value = yearMonthData[y] || [];
  selectedMonth.value = "";
});

watch(deleteYear, () => {
  deleteMonth.value = "";
  deleteMessage.value = "";
  deleteError.value = "";
  deleteSlipCount.value = 0;
});

watch(deleteMonth, () => {
  deleteMessage.value = "";
  deleteError.value = "";
  if (deleteMonth.value) {
    fetchDeleteSlipCount();
  } else {
    deleteSlipCount.value = 0;
  }
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

// --- Delete Month Slips ---
const deleteMonthSlips = async () => {
  if (!deleteYear.value || !deleteMonth.value) {
    deleteError.value = "กรุณาเลือกเดือนและปี";
    return;
  }

  const confirmMsg = `คุณแน่ใจหรือไม่ที่จะลบสลิปทั้งหมด ${deleteSlipCount.value} รายการ\nของเดือน ${getMonthName(deleteMonth.value)} พ.ศ. ${deleteYear.value}?\n\n⚠️ การกระทำนี้ไม่สามารถย้อนกลับได้!`;
  
  if (!confirm(confirmMsg)) return;

  deleteLoading.value = true;
  deleteMessage.value = "";
  deleteError.value = "";

  try {
    // Use the bulk delete endpoint
    const result = await api(
      `/files/delete-month?year=${deleteYear.value}&month=${deleteMonth.value}`, 
      { method: "DELETE" }
    );
    
    if (result.success) {
      deleteMessage.value = `✅ ${result.message}`;
      
      // Refresh data
      await loadUploadedFiles();
      await fetchAvailableMonths();
      
      // Reset form
      deleteYear.value = "";
      deleteMonth.value = "";
      deleteSlipCount.value = 0;
      
      // Clear message after 5 seconds
      setTimeout(() => {
        deleteMessage.value = "";
      }, 5000);
    } else {
      throw new Error(result.error || "ไม่สามารถลบได้");
    }

  } catch (e) {
    deleteError.value = e.message || "เกิดข้อผิดพลาดในการลบ";
    setTimeout(() => {
      deleteError.value = "";
    }, 5000);
  } finally {
    deleteLoading.value = false;
  }
};

// --- Handlers ---
const handleLogin = () => { isLoggingIn.value = true; $liff.login(); };
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
    const data = await api("/files/list?limit=1000");
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
      await fetchAvailableMonths();
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

// New function to add admin
const addAdmin = async () => {
  if (!newAdminEmail.value || !newAdminEmail.value.includes('@')) {
    adminManageError.value = "กรุณาระบุอีเมลที่ถูกต้อง";
    return;
  }
  
  adminManageLoading.value = true;
  adminManageMessage.value = "";
  adminManageError.value = "";
  
  try {
    const data = await api("/admin/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        email: newAdminEmail.value,
        requesterEmail: userEmail.value
      })
    });
    
    if (data.success) {
      adminManageMessage.value = data.message;
      newAdminEmail.value = "";
      await loadAdminList();
      
      setTimeout(() => {
        adminManageMessage.value = "";
      }, 3000);
    } else {
      throw new Error(data.error);
    }
  } catch (e) {
    adminManageError.value = e.message;
    setTimeout(() => {
      adminManageError.value = "";
    }, 3000);
  } finally {
    adminManageLoading.value = false;
  }
};

// New function to remove admin
const removeAdmin = async (email) => {
  if (!confirm(`คุณแน่ใจว่าจะลบ Admin: ${email}?`)) return;
  
  adminManageLoading.value = true;
  adminManageMessage.value = "";
  adminManageError.value = "";
  
  try {
    const data = await api(`/admin/remove?email=${email}&requesterEmail=${userEmail.value}`, {
      method: "DELETE"
    });
    
    if (data.success) {
      adminManageMessage.value = data.message;
      await loadAdminList();
      
      setTimeout(() => {
        adminManageMessage.value = "";
      }, 3000);
    } else {
      throw new Error(data.error);
    }
  } catch (e) {
    adminManageError.value = e.message;
    setTimeout(() => {
      adminManageError.value = "";
    }, 3000);
  } finally {
    adminManageLoading.value = false;
  }
};
</script>

<style scoped>
@import url('@/assets/css/tailwind.css');
</style>