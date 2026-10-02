import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';

const styles = {
    container: {
        minHeight: '100vh',
        backgroundColor: '#f3f2ef',
        padding: '40px',
    },
    card: {
        backgroundColor: '#fff',
        borderRadius: '8px',
        padding: '30px',
        maxWidth: '600px',
        margin: '0 auto',
        boxShadow: '0 0 10px rgba(0,0,0,0.1)',
    },
    title: {
        fontSize: '24px',
        fontWeight: 'bold',
        marginBottom: '20px',
        color: '#000',
    },
    form: {
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
    },
    label: {
        fontSize: '14px',
        fontWeight: '500',
        color: '#666',
    },
    input: {
        width: '100%',
        padding: '12px',
        border: '1px solid #e0e0e0',
        borderRadius: '4px',
        fontSize: '14px',
    },
    textarea: {
        width: '100%',
        padding: '12px',
        border: '1px solid #e0e0e0',
        borderRadius: '4px',
        minHeight: '100px',
        fontSize: '14px',
        resize: 'vertical',
    },
    imagePreview: {
        width: '150px',
        height: '150px',
        borderRadius: '75px',
        backgroundColor: '#e0e0e0',
        marginBottom: '20px',
        overflow: 'hidden',
    },
    button: {
        backgroundColor: '#0a66c2',
        color: '#fff',
        border: 'none',
        padding: '12px',
        borderRadius: '24px',
        fontSize: '16px',
        fontWeight: '600',
        cursor: 'pointer',
        '&:hover': {
            backgroundColor: '#084482',
        },
    },
    error: {
        color: '#d32f2f',
        fontSize: '14px',
        marginTop: '5px',
    },
    subscriberCount: {
        fontSize: '14px',
        color: '#666',
        marginBottom: '15px',
        fontWeight: '500',
    },
};

const Profile = () => {
    const [profile, setProfile] = useState({
        username: '',
        about: '',
        profile_picture: null,
        subscriber_count: 0,
    });
    const [error, setError] = useState('');
    const [imagePreview, setImagePreview] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        loadProfile();
        // Set up auto-refresh every 5 seconds to detect new subscribers
        const interval = setInterval(loadProfile, 5000);
        return () => clearInterval(interval);
    }, []);
    
    // Add API_BASE_URL import at the top
    const API_BASE_URL = 'http://localhost:8000';

    const loadProfile = async () => {
        try {
            console.log('Token:', localStorage.getItem('token')); // Debug line
            const response = await authService.loadProfile();
            console.log('Profile response:', response.data); // Debug line
            setProfile(response.data);
            if (response.data.profile_picture) {
                setImagePreview(`${API_BASE_URL}${response.data.profile_picture}`);
            }
        } catch (error) {
            console.error('Error loading profile:', error);
            console.error('Error details:', error.response?.data); // Debug line
            if (error.response?.status === 401) {
                navigate('/login');
            }
        }
    };

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setImagePreview(reader.result);
            };
            reader.readAsDataURL(file);
            setProfile({ ...profile, profile_picture: file });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const formData = new FormData();
            formData.append('about', profile.about || '');
            
            if (profile.profile_picture instanceof File) {
                formData.append('profile_pic', profile.profile_picture);
            }

            const response = await authService.updateProfile(formData);
            console.log('Profile update response:', response.data);
            
            // Update the profile with the new data
            setProfile(response.data);
            if (response.data.profile_picture) {
                setImagePreview(`${API_BASE_URL}${response.data.profile_picture}`);
            }
            
            setError('');
            // Show success message or redirect
            navigate('/dashboard');
        } catch (error) {
            console.error('Profile update error:', error);
            setError(error.response?.data?.detail || 'Error updating profile');
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h1 style={styles.title}>Edit Profile</h1>
                <form onSubmit={handleSubmit} style={styles.form}>
                    <div style={styles.imagePreview}>
                        {imagePreview && (
                            <img
                                src={imagePreview}
                                alt="Profile"
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            />
                        )}
                    </div>

                    <div style={styles.subscriberCount}>
                        Subscribers: {profile.subscriber_count || 0}
                    </div>

                    <div>
                        <label htmlFor="profile-picture" style={styles.label}>Profile Picture</label>
                        <input
                            id="profile-picture"
                            type="file"
                            accept="image/*"
                            onChange={handleImageChange}
                            style={styles.input}
                        />
                    </div>

                    <div>
                        <label htmlFor="username" style={styles.label}>Username</label>
                        <input
                            id="username"
                            type="text"
                            value={profile.username}
                            onChange={(e) => setProfile({ ...profile, username: e.target.value })}
                            style={styles.input}
                            disabled
                        />
                    </div>

                    <div>
                        <label htmlFor="about" style={styles.label}>About</label>
                        <textarea
                            id="about"
                            value={profile.about || ''}
                            onChange={(e) => setProfile({ ...profile, about: e.target.value })}
                            style={styles.textarea}
                            placeholder="Write something about yourself..."
                        />
                    </div>

                    {error && <div style={styles.error}>{error}</div>}

                    <button type="submit" style={styles.button}>
                        Save Changes
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Profile;