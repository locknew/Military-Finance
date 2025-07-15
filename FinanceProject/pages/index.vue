<template>
  <div
    class="min-h-screen bg-military-gradient flex items-center justify-center p-5"
  >
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
      <div class="header">
        <span class="header-icon">🪖</span>
        <h1 class="header-title">ตรวจสอบสลิปเงินเดือน</h1>
        <p class="header-subtitle">ระบบตรวจสอบสลิปเงินเดือนทหาร</p>
      </div>

      <div class="form-group">
        <label class="form-label">เลขบัญชี</label>
        <input
          v-model="account"
          placeholder="กรอกเลขบัญชีของคุณ"
          class="input"
          type="text"
        />
      </div>

      <div class="form-group">
        <label class="form-label">เลือกช่วงเวลา</label>
        <div class="grid">
          <select v-model="selectedYear" class="input">
            <option value="">เลือกปี</option>
            <option v-for="y in availableYears" :key="y" :value="y">
              {{ y }}
            </option>
          </select>

          <select
            v-model="selectedMonth"
            class="input"
            :disabled="!selectedYear"
          >
            <option value="">เลือกเดือน</option>
            <option v-for="m in availableMonths" :key="m" :value="m">
              {{ m }}
            </option>
          </select>
        </div>
      </div>

      <button @click="getSlip" class="btn" :disabled="loading">
        <span v-if="loading" class="loading"></span>
        <span v-else>📥</span>
        {{ loading ? "กำลังโหลด..." : "แสดงสลิปเงินเดือน" }}
      </button>

      <div v-if="pdfUrl" class="pdf-container slide-up">
        <iframe :src="pdfUrl" class="pdf-iframe"></iframe>
      </div>

      <!-- Admin Section -->
      <div v-if="isAdminUser" class="admin-section slide-up">
        <div class="admin-header">
          <h3 class="admin-title">อัปโหลดไฟล์ PDF</h3>
          <span class="admin-badge">ADMIN</span>
        </div>

        <div class="form-group">
          <div class="file-input">
            <input
              id="file-upload"
              type="file"
              accept=".pdf"
              @change="handleFileUpload"
              ref="fileInput"
              class="hidden"
            />
            <label for="file-upload" class="file-input-label">
              📄 คลิกเพื่อเลือกไฟล์ PDF
            </label>
          </div>

          <!-- File preview -->
          <div v-if="selectedFile" class="file-preview">
            <div class="file-info">
              <span class="file-name">{{ selectedFile.name }}</span>
              <span class="file-size">({{ formatFileSize(selectedFile.size) }})</span>
            </div>
            <button @click="clearFile" class="clear-btn">✕</button>
          </div>
        </div>

        <button
          @click="uploadPDF"
          class="btn"
          :disabled="uploadLoading || !selectedFile"
        >
          <span v-if="uploadLoading" class="loading"></span>
          <span v-else>🚀</span>
          {{ uploadLoading ? "กำลังอัปโหลด..." : "อัปโหลด" }}
        </button>

        <div v-if="uploadMessage" class="success-message">
          {{ uploadMessage }}
        </div>

        <div v-if="uploadUrl" class="success-message">
          ✅ ไฟล์อัปโหลดแล้ว:
          <a :href="uploadUrl" target="_blank" class="underline text-blue-600">
            {{ uploadUrl }}
          </a>
        </div>

        <div v-if="uploadError" class="error-message">
          ❌ {{ uploadError }}
        </div>

        <!-- File list section -->
        <div v-if="uploadedFiles.length > 0" class="uploaded-files-section">
          <h4 class="files-title">ไฟล์ที่อัปโหลดแล้ว</h4>
          <div class="files-list">
            <div v-for="file in uploadedFiles" :key="file.name" class="file-item">
              <div class="file-details">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">{{ formatFileSize(file.size) }}</span>
                <span class="file-date">{{ formatDate(file.uploadedAt) }}</span>
              </div>
              <div class="file-actions">
                <a :href="file.url" target="_blank" class="view-btn">👁️</a>
                <button @click="deleteFile(file.name)" class="delete-btn">🗑️</button>
              </div>
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
const account = ref("");
const availableYears = ref([]);
const availableMonths = ref([]);
const selectedYear = ref("");
const selectedMonth = ref("");
const pdfUrl = ref("");
const uploadMessage = ref("");
const uploadError = ref("");
const uploadUrl = ref("");
const isAdminUser = ref(false);
const loading = ref(false);
const uploadLoading = ref(false);
const isLoggedIn = ref(false);
const isLoggingIn = ref(false);
const userProfile = ref(null);

// File upload related
const selectedFile = ref(null);
const fileInput = ref(null);
const uploadedFiles = ref([]);

onMounted(async () => {
  try {
    // Initialize LIFF
    await $liff.init({
      liffId: import.meta.env.VITE_LIFF_ID,
    });

    if ($liff.isLoggedIn()) {
      isLoggedIn.value = true;

      // Get user profile
      userProfile.value = await $liff.getProfile();

      // Check if user is admin
      if (isAdmin(userProfile.value.userId)) {
        isAdminUser.value = true;
        // Load uploaded files for admin
        await loadUploadedFiles();
      }

      // Fetch available months
      await fetchAvailableMonths();
    }
  } catch (error) {
    console.error("LIFF initialization failed:", error);
  }
});

const handleLogin = async () => {
  isLoggingIn.value = true;
  try {
    $liff.login();
  } catch (error) {
    console.error("Login failed:", error);
    isLoggingIn.value = false;
  }
};

const fetchAvailableMonths = async () => {
  try {
    const res = await fetch(
      "https://locknew.pythonanywhere.com/api/available-months"
    );
    const data = await res.json();
    availableYears.value = Object.keys(data);

    watch(selectedYear, (newYear) => {
      availableMonths.value = data[newYear] || [];
      selectedMonth.value = "";
    });
  } catch (error) {
    console.error("Error fetching available months:", error);
    // Fallback data
    availableYears.value = ["2024", "2023", "2022", "2021"];
  }
};

const getSlip = async () => {
  if (!account.value || !selectedYear.value || !selectedMonth.value) {
    alert("กรุณากรอกข้อมูลให้ครบถ้วน");
    return;
  }

  loading.value = true;

  try {
    const res = await fetch("https://locknew.pythonanywhere.com/api/get-slip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account: account.value,
        month: selectedMonth.value,
        year: selectedYear.value,
      }),
    });
    const data = await res.json();
    pdfUrl.value = data.url;
  } catch (error) {
    console.error("Error fetching slip:", error);
    alert("เกิดข้อผิดพลาดในการดึงสลิป");
  } finally {
    loading.value = false;
  }
};

const handleFileUpload = (event) => {
  const file = event.target.files[0];
  
  if (file) {
    // Validate file type
    if (file.type !== 'application/pdf') {
      uploadError.value = 'กรุณาเลือกไฟล์ PDF เท่านั้น';
      return;
    }
    
    // Validate file size (10MB max)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      uploadError.value = 'ไฟล์มีขนาดใหญ่เกินไป (สูงสุด 10MB)';
      return;
    }
    
    selectedFile.value = file;
    uploadError.value = '';
    uploadMessage.value = '';
    uploadUrl.value = '';
  }
};

const clearFile = () => {
  selectedFile.value = null;
  uploadMessage.value = '';
  uploadUrl.value = '';
  uploadError.value = '';
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

const uploadPDF = async () => {
  if (!selectedFile.value) {
    uploadError.value = 'กรุณาเลือกไฟล์ PDF';
    return;
  }

  uploadLoading.value = true;
  uploadError.value = '';
  uploadMessage.value = '';
  uploadUrl.value = '';

  try {
    // Create FormData for file upload
    const formData = new FormData();
    formData.append('file', selectedFile.value);
    formData.append('uploadedBy', userProfile.value.userId);
    formData.append('uploadedAt', new Date().toISOString());

    // Upload to Nuxt server API
    const response = await $fetch('/api/upload-slip', {
      method: 'POST',
      body: formData
    });

    if (response.success) {
      uploadMessage.value = 'อัปโหลดไฟล์สำเร็จ!';
      uploadUrl.value = response.url;
      
      // Reload uploaded files list
      await loadUploadedFiles();
      
      // Clear the form after successful upload
      setTimeout(() => {
        clearFile();
      }, 2000);
    } else {
      throw new Error(response.error || 'เกิดข้อผิดพลาดในการอัปโหลด');
    }

  } catch (error) {
    console.error('Upload error:', error);
    uploadError.value = error.message || 'เกิดข้อผิดพลาดในการอัปโหลดไฟล์';
  } finally {
    uploadLoading.value = false;
  }
};

const loadUploadedFiles = async () => {
  try {
    const response = await $fetch('/api/files/list');
    uploadedFiles.value = response.files || [];
  } catch (error) {
    console.error('Error loading files:', error);
  }
};

const deleteFile = async (filename) => {
  if (!confirm('คุณแน่ใจหรือไม่ที่จะลบไฟล์นี้?')) {
    return;
  }

  try {
    await $fetch(`/api/files/delete?filename=${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    });
    
    // Remove from local list
    uploadedFiles.value = uploadedFiles.value.filter(file => file.name !== filename);
    
    // Show success message
    uploadMessage.value = 'ลบไฟล์สำเร็จ!';
    setTimeout(() => {
      uploadMessage.value = '';
    }, 3000);
    
  } catch (error) {
    console.error('Error deleting file:', error);
    uploadError.value = 'เกิดข้อผิดพลาดในการลบไฟล์';
  }
};

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('th-TH', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};
</script>
<style scoped>
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
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
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

.pdf-container {
  margin-top: 32px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.pdf-iframe {
  width: 100%;
  height: 400px;
  border: none;
  border-radius: 16px;
}

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

.success-message {
  background: #c6f6d5;
  color: #22543d;
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
</style>