import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import { isValidEmail, getEmailValidationMessage } from '../utils/validation';

const styles = {
    container: {
        minHeight: '100vh',
        backgroundColor: '#f3f2ef',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
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
    backToLogin: {
        textAlign: 'center',
        marginTop: '20px',
    },
    link: {
        color: '#0a66c2',
        textDecoration: 'none',
        cursor: 'pointer',
        '&:hover': {
            textDecoration: 'underline',
        },
    },
};

const ForgotPassword = () => {
    const [email, setEmail] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!isValidEmail(email)) {
            setError(getEmailValidationMessage());
            return;
        }

        try {
            await authService.forgotPassword(email);
            setError(''); 
            setSuccess('OTP has been sent to your email. Please check your inbox.');
            localStorage.setItem('resetEmail', email);
            setTimeout(() => {
                navigate('/reset-password');
            }, 2000);
        } catch (error) {
            setSuccess(''); 
            setError(error.response?.data?.detail || 'Error sending OTP');
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.formCard}>
                <h1 style={styles.title}>Forgot Password</h1>
                <form onSubmit={handleSubmit} style={styles.form}>
                    <input
                        type="email"
                        placeholder="Enter your email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        pattern="^[a-zA-Z][a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                        title={getEmailValidationMessage()}
                        style={styles.input}
                        required
                    />
                    <button type="submit" style={styles.button}>
                        Send OTP
                    </button>
                    {error && <div style={styles.error}>{error}</div>}
                    {success && <div style={styles.success}>{success}</div>}
                </form>
                <div style={styles.backToLogin}>
                    <span 
                        style={styles.link} 
                        onClick={() => navigate('/login')}
                    >
                        Back to Login
                    </span>
                </div>
            </div>
        </div>
    );
};

export default ForgotPassword;