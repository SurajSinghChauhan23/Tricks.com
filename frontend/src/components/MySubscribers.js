import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService, getImageUrl } from '../services/api';

const styles = {
    container: {
        minHeight: '100vh',
        backgroundColor: '#f3f2ef',
        padding: '30px',
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        marginBottom: '24px',
        gap: '12px',
    },
    backBtn: {
        backgroundColor: 'transparent',
        border: '1.5px solid #0a66c2',
        color: '#0a66c2',
        padding: '8px 16px',
        borderRadius: '16px',
        cursor: 'pointer',
        fontWeight: '600',
        fontSize: '14px',
    },
    title: {
        fontSize: '24px',
        fontWeight: 'bold',
        color: '#333',
    },
    subtitle: {
        fontSize: '14px',
        color: '#888',
        marginBottom: '24px',
        maxWidth: '700px',
        margin: '0 auto 24px',
        textAlign: 'center',
    },
    grid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
        gap: '20px',
        maxWidth: '900px',
        margin: '0 auto',
    },
    card: {
        backgroundColor: '#fff',
        borderRadius: '12px',
        padding: '24px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        position: 'relative',
    },
    avatar: {
        width: '72px',
        height: '72px',
        borderRadius: '36px',
        backgroundColor: '#e0e0e0',
        marginBottom: '12px',
        overflow: 'hidden',
        flexShrink: 0,
    },
    name: {
        fontSize: '17px',
        fontWeight: 'bold',
        color: '#333',
        marginBottom: '4px',
    },
    about: {
        fontSize: '13px',
        color: '#888',
        marginBottom: '16px',
    },
    chatBtn: {
        backgroundColor: '#0a66c2',
        color: '#fff',
        border: 'none',
        padding: '8px 20px',
        borderRadius: '16px',
        cursor: 'pointer',
        fontWeight: '600',
        fontSize: '14px',
        width: '100%',
    },
    messageBadge: {
        position: 'absolute',
        top: '14px',
        right: '14px',
        backgroundColor: '#e53935',
        color: '#fff',
        fontSize: '11px',
        fontWeight: '700',
        padding: '3px 8px',
        borderRadius: '10px',
    },
    empty: {
        textAlign: 'center',
        color: '#888',
        marginTop: '60px',
        fontSize: '16px',
        lineHeight: '1.7',
    },
    emptyIcon: {
        fontSize: '48px',
        marginBottom: '12px',
    },
};

const MySubscribers = () => {
    const [subscribers, setSubscribers] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        loadSubscribers();
        // Poll every 10s to refresh message indicators
        const interval = setInterval(loadSubscribers, 10000);
        return () => clearInterval(interval);
    }, []);

    const loadSubscribers = async () => {
        try {
            const response = await authService.getMySubscribers();
            setSubscribers(response.data);
        } catch (error) {
            console.error('Error loading subscribers:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <button style={styles.backBtn} onClick={() => navigate('/dashboard')}>
                    ← Back
                </button>
                <div style={styles.title}>👥 My Subscribers</div>
            </div>

            {loading ? (
                <div style={styles.empty}>Loading...</div>
            ) : subscribers.length === 0 ? (
                <div style={styles.empty}>
                    <div style={styles.emptyIcon}>📭</div>
                    No one has subscribed to you yet.<br />
                    Share your posts to attract subscribers!
                </div>
            ) : (
                <>
                    <div style={styles.subtitle}>
                        {subscribers.length} subscriber{subscribers.length !== 1 ? 's' : ''} · Click Chat to reply to messages
                    </div>
                    <div style={styles.grid}>
                        {subscribers.map((sub) => (
                            <div key={sub.user_id} style={styles.card}>
                                {/* Red dot if they've sent you a message */}
                                {sub.has_message && (
                                    <div style={styles.messageBadge}>💬 Message</div>
                                )}

                                <div style={styles.avatar}>
                                    {sub.profile_pic ? (
                                        <img
                                            src={getImageUrl(sub.profile_pic)}
                                            alt={sub.username}
                                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                        />
                                    ) : (
                                        <div style={{
                                            width: '100%', height: '100%',
                                            display: 'flex', alignItems: 'center',
                                            justifyContent: 'center',
                                            fontSize: '28px', color: '#aaa',
                                        }}>
                                            👤
                                        </div>
                                    )}
                                </div>

                                <div style={styles.name}>{sub.username}</div>
                                <div style={styles.about}>{sub.about || 'Subscriber'}</div>

                                <button
                                    style={styles.chatBtn}
                                    onClick={() => navigate(`/chat/${sub.user_id}`)}
                                >
                                    💬 Chat
                                </button>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
};

export default MySubscribers;