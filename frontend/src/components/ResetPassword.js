import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import { isValidPassword, getPasswordValidationMessage } from '../utils/validation';

const styles = {
    container: {
        minHeight: '100vh',
        backgroundColor: '#f3f2ef',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
    },
    passwordContainer: {
        position: 'relative',
        width: '100%',
    },
    passwordToggle: {
        position: 'absolute',
        right: '10px',
        top: '50%',
        transform: 'translateY(-50%)',
        cursor: 'pointer',
        border: 'none',
        background: 'none',
        color: '#000',
        padding: '4px',
    },
    formCard: {
        backgroundColor: '#fff',
        borderRadius: '8px',
        padding: '30px',
        width: '100%',
        maxWidth: '400px',
        boxShadow: '0 0 10px rgba(0,0,0,0.1)',
    },
    title: {
        fontSize: '24px',
        fontWeight: 'bold',
        marginBottom: '20px',
        textAlign: 'center',
        color: '#000',
    },
    form: {
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
    },
    input: {
        width: '100%',
        padding: '12px',
        border: '1px solid #e0e0e0',
        borderRadius: '4px',
        fontSize: '14px',
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
        marginTop: '10px',
        textAlign: 'center',
    },
    success: {
        color: '#2e7d32',
        fontSize: '14px',
        marginTop: '10px',
        textAlign: 'center',
    },
};

const ResetPassword = () => {
    const [formData, setFormData] = useState({
        otp: '',
        newPassword: '',
        confirmPassword: '',
    });
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const navigate = useNavigate();

    // Remove warning about unused variables
    const toggleNewPassword = () => setShowNewPassword(!showNewPassword);
    const toggleConfirmPassword = () => setShowConfirmPassword(!showConfirmPassword);

    const handleSubmit = async (e) => {
        e.preventDefault();

        
        if (!isValidPassword(formData.newPassword)) {
            setError(getPasswordValidationMessage());
            return;
        }

    
        if (formData.newPassword !== formData.confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        try {
            await authService.resetPassword({
                otp: formData.otp,
                newpassword: formData.newPassword,
            });
            setError(''); 
            setSuccess('Password reset successful! Redirecting to login...');
            
            localStorage.removeItem('resetEmail');
            setTimeout(() => {
                navigate('/login');
            }, 2000);
        } catch (error) {
            setSuccess(''); 
            setError(error.response?.data?.detail || 'Error resetting password');
        }
    };

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value,
        });
    };

    return (
        <div style={styles.container}>
            <div style={styles.formCard}>
                <h1 style={styles.title}>Reset Password</h1>
                <form onSubmit={handleSubmit} style={styles.form}>
                    <input
                        type="text"
                        name="otp"
                        placeholder="Enter OTP"
                        value={formData.otp}
                        onChange={handleChange}
                        style={styles.input}
                        required
                    />
                    <div style={styles.passwordContainer}>
                        <input
                            type={showNewPassword ? "text" : "password"}
                            name="newPassword"
                            placeholder="New Password"
                            minLength={9}
                            title={getPasswordValidationMessage()}
                            value={formData.newPassword}
                            onChange={handleChange}
                            style={styles.input}
                            required
                        />
                        <button
                            type="button"
                            style={styles.passwordToggle}
                            onClick={toggleNewPassword}
                            tabIndex="-1"
                            aria-label={showNewPassword ? "Hide password" : "Show password"}
                        >                            {showNewPassword ? "Hide" : "Show"}</button>
                    </div>
                    <div style={styles.passwordContainer}>
                        <input
                            type={showConfirmPassword ? "text" : "password"}
                            name="confirmPassword"
                            placeholder="Confirm New Password"
                            minLength={9}
                            title="Must match the password above"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            style={styles.input}
                            required
                        />
                        <button
                            type="button"
                            style={styles.passwordToggle}
                            onClick={toggleConfirmPassword}
                            tabIndex="-1"
                            aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                        >
                            {showConfirmPassword ? "Hide" : "Show"}
                        </button>
                    </div>
                    <button type="submit" style={styles.button}>
                        Reset Password
                    </button>
                    {error && <div style={styles.error}>{error}</div>}
                    {success && <div style={styles.success}>{success}</div>}
                </form>
            </div>
        </div>
    );
};

export default ResetPassword;