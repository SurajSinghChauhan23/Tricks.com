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
    grid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
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
    },
    avatar: {
        width: '72px',
        height: '72px',
        borderRadius: '36px',
        backgroundColor: '#e0e0e0',
        marginBottom: '12px',
        overflow: 'hidden',
    },
    name: {
        fontSize: '17px',
        fontWeight: 'bold',
        color: '#333',
        marginBottom: '6px',
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
    empty: {
        textAlign: 'center',
        color: '#888',
        marginTop: '60px',
        fontSize: '16px',
    },
};

const Community = () => {
    const [creators, setCreators] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        checkAccessAndLoad();
    }, []);

    const checkAccessAndLoad = async () => {
        try {
            loadCreators();
        } catch (error) {
            console.error('Error loading community:', error);
        }
    };

    const loadCreators = async () => {
        try {
            const response = await authService.getSubscribedCreators();
            setCreators(response.data);
        } catch (error) {
            console.error('Error loading creators:', error);
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
                <div style={styles.title}>🌐 Community</div>
            </div>

            {loading ? (
                <div style={styles.empty}>Loading...</div>
            ) : creators.length === 0 ? (
                <div style={styles.empty}>
                    You haven't subscribed to any community creators yet.<br />
                    Subscribe to a creator's post on the dashboard to chat with them!
                </div>
            ) : (
                <div style={styles.grid}>
                    {creators.map((creator) => (
                        <div key={creator.user_id} style={styles.card}>
                            <div style={styles.avatar}>
                                {creator.profile_pic ? (
                                    <img
                                        src={getImageUrl(creator.profile_pic)}
                                        alt={creator.username}
                                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    />
                                ) : (
                                    <div style={{
                                        width: '100%', height: '100%',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontSize: '28px', color: '#aaa'
                                    }}>
                                        👤
                                    </div>
                                )}
                            </div>
                            <div style={styles.name}>{creator.username}</div>
                            <div style={styles.about}>{creator.about || 'Community Creator'}</div>
                            <button
                                style={styles.chatBtn}
                                onClick={() => navigate(`/chat/${creator.user_id}`)}
                            >
                                💬 Chat
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default Community;