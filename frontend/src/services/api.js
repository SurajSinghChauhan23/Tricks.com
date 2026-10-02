import axios from 'axios';

export const API_BASE_URL = 'http://localhost:8000';

export const getImageUrl = (path) => {
    if (!path) return null;
    return `${API_BASE_URL}${path}`;
};

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    }
});

export const authService = {
    register: (userData) => api.post('/api/register', userData).then(res => {
        if (res.data.user_type) localStorage.setItem('user_type', res.data.user_type);
        return res;
    }),
    login: (credentials) => api.post('/api/login', credentials).then(res => {
        if (res.data.user_type) localStorage.setItem('user_type', res.data.user_type);
        return res;
    }),
    forgotPassword: (email) => api.post('/api/forgotpassword', { email }),
    resetPassword: (data) => api.post('/api/resetpassword', data),
    loadProfile: () => api.get('/api/loadprofile'),
    updateProfile: (formData) => api.put('/api/update-profile', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }),
    uploadPost: (postData) => api.post('/api/posts', postData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }),
    getPosts: () => api.get('/api/posts'),
    reportPost: (postId) => api.post(`/api/posts/${postId}/report`),
    subscribePost: (postId) => api.post(`/api/posts/${postId}/subscribe`),
    joinCommunity: (data) => api.post('/api/join-community', data),
    communityStatus: () => api.get('/api/community-status'),
    getSubscribedCreators: () => api.get('/api/community/creators'),
    getMySubscribers: () => api.get('/api/community/subscribers'),
    getChatHistory: (userId) => api.get(`/api/chat/${userId}`),
    sendMessage: (userId, content) => api.post(`/api/chat/${userId}`, { content }),
    // QR / Macrodroid payment flow
    verifyPayment: (data) => api.post('/api/verify-payment', data),          // data: { transaction_id, source_type, source_id, amount? }
    boostPost: (data) => api.post('/api/boost-post', data),
    // Poll this after verifyPayment; status: paid|pending|unpaid|none
    checkPaymentStatus: (source_type, source_id) =>
        api.get('/api/payment-status', { params: { source_type, source_id } }),
    // Check community-join payment status for the current user (no params needed)
    checkCommunityPaymentStatus: () => api.get('/api/community-payment-status'),
};

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = token;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

export default api;
