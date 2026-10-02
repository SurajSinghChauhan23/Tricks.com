import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { authService, getImageUrl } from '../services/api';

const styles = {
    container: {
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        backgroundColor: '#f3f2ef',
    },
    header: {
        backgroundColor: '#fff',
        padding: '14px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
        zIndex: 10,
    },
    backBtn: {
        backgroundColor: 'transparent',
        border: '1.5px solid #0a66c2',
        color: '#0a66c2',
        padding: '6px 14px',
        borderRadius: '14px',
        cursor: 'pointer',
        fontWeight: '600',
        fontSize: '13px',
    },
    avatar: {
        width: '42px',
        height: '42px',
        borderRadius: '21px',
        backgroundColor: '#e0e0e0',
        overflow: 'hidden',
        flexShrink: 0,
    },
    headerName: {
        fontSize: '17px',
        fontWeight: 'bold',
        color: '#333',
    },
    messagesArea: {
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
    },
    messageBubble: (isMe) => ({
        maxWidth: '65%',
        padding: '10px 14px',
        borderRadius: isMe ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        backgroundColor: isMe ? '#0a66c2' : '#fff',
        color: isMe ? '#fff' : '#333',
        alignSelf: isMe ? 'flex-end' : 'flex-start',
        boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
        fontSize: '15px',
        lineHeight: '1.4',
    }),
    messageTime: (isMe) => ({
        fontSize: '11px',
        color: isMe ? 'rgba(255,255,255,0.7)' : '#aaa',
        marginTop: '4px',
        textAlign: isMe ? 'right' : 'left',
    }),
    messageSender: {
        fontSize: '12px',
        color: '#888',
        marginBottom: '2px',
    },
    inputArea: {
        backgroundColor: '#fff',
        padding: '14px 20px',
        display: 'flex',
        gap: '10px',
        alignItems: 'center',
        boxShadow: '0 -1px 4px rgba(0,0,0,0.08)',
    },
    input: {
        flex: 1,
        padding: '10px 16px',
        border: '1.5px solid #e0e0e0',
        borderRadius: '24px',
        fontSize: '15px',
        outline: 'none',
    },
    sendBtn: {
        backgroundColor: '#0a66c2',
        color: '#fff',
        border: 'none',
        padding: '10px 20px',
        borderRadius: '24px',
        cursor: 'pointer',
        fontWeight: '600',
        fontSize: '14px',
        flexShrink: 0,
    },
    emptyChat: {
        textAlign: 'center',
        color: '#aaa',
        marginTop: '40px',
        fontSize: '15px',
    },
};

const formatTime = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const Chat = () => {
    const { userId } = useParams();
    const [chatData, setChatData] = useState(null);
    const [messageText, setMessageText] = useState('');
    const [sending, setSending] = useState(false);
    const [error, setError] = useState('');
    const messagesEndRef = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        loadChat();
        // Poll for new messages every 3 seconds
        const interval = setInterval(loadChat, 3000);
        return () => clearInterval(interval);
    }, [userId]);

    useEffect(() => {
        scrollToBottom();
    }, [chatData]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const loadChat = async () => {
        try {
            const response = await authService.getChatHistory(userId);
            setChatData(response.data);
        } catch (error) {
            if (error.response?.status === 403) {
                setError('You must be subscribed to this creator to chat.');
            } else {
                console.error('Error loading chat:', error);
            }
        }
    };

    const handleSend = async (e) => {
        e.preventDefault();
        if (!messageText.trim() || sending) return;

        setSending(true);
        try {
            const newMsg = await authService.sendMessage(userId, messageText.trim());
            setMessageText('');
            // Add message instantly to UI
            setChatData(prev => ({
                ...prev,
                messages: [...(prev?.messages || []), newMsg.data],
            }));
        } catch (error) {
            console.error('Error sending message:', error);
        } finally {
            setSending(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend(e);
        }
    };

    if (error) {
        return (
            <div style={styles.container}>
                <div style={styles.header}>
                    <button style={styles.backBtn} onClick={() => navigate('/community')}>← Back</button>
                    <div style={styles.headerName}>Chat</div>
                </div>
                <div style={{ textAlign: 'center', marginTop: '60px', color: '#cc0000', fontSize: '16px' }}>
                    {error}
                </div>
            </div>
        );
    }

    const otherUser = chatData?.other_user;

    return (
        <div style={styles.container}>
            {/* Header */}
            <div style={styles.header}>
                <button style={styles.backBtn} onClick={() => navigate('/community')}>← Back</button>
                <div style={styles.avatar}>
                    {otherUser?.profile_pic ? (
                        <img
                            src={getImageUrl(otherUser.profile_pic)}
                            alt={otherUser.username}
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                    ) : (
                        <div style={{
                            width: '100%', height: '100%',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '20px',
                        }}>👤</div>
                    )}
                </div>
                <div style={styles.headerName}>{otherUser?.username || 'Chat'}</div>
            </div>

            {/* Messages */}
            <div style={styles.messagesArea}>
                {!chatData ? (
                    <div style={styles.emptyChat}>Loading messages...</div>
                ) : chatData.messages.length === 0 ? (
                    <div style={styles.emptyChat}>
                        No messages yet. Say hello! 👋
                    </div>
                ) : (
                    chatData.messages.map((msg) => (
                        <div key={msg.id}>
                            {!msg.is_mine && (
                                <div style={styles.messageSender}>{msg.sender_username}</div>
                            )}
                            <div style={styles.messageBubble(msg.is_mine)}>
                                {msg.content}
                            </div>
                            <div style={styles.messageTime(msg.is_mine)}>
                                {formatTime(msg.timestamp)}
                            </div>
                        </div>
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form style={styles.inputArea} onSubmit={handleSend}>
                <input
                    style={styles.input}
                    type="text"
                    placeholder="Type a message..."
                    value={messageText}
                    onChange={(e) => setMessageText(e.target.value)}
                    onKeyDown={handleKeyDown}
                />
                <button
                    type="submit"
                    style={{ ...styles.sendBtn, opacity: sending ? 0.7 : 1 }}
                    disabled={sending || !messageText.trim()}
                >
                    Send ➤
                </button>
            </form>
        </div>
    );
};

export default Chat;