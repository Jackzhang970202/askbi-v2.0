/**
 * Global Streaming Manager
 * Handles streaming updates for messages independently of component lifecycle.
 */

const StreamingManager = (() => {
    // Stores streaming status for all messages
    const streamingStates = new Map(); // { [messageKey]: { stage, displayedLength, timer, chatId, messageIndex, onUpdate } }
    
    // Generate unique key for a message
    const getMessageKey = (chatId, messageIndex) => `${chatId}_${messageIndex}`;
    
    // Start streaming process
    const startStreaming = (chatId, messageIndex, message, onUpdate) => {
        const key = getMessageKey(chatId, messageIndex);
        
        // 如果已存在，更新 onUpdate 并基于最新 message 继续推进状态（避免卡在 thinking）
        if (streamingStates.has(key)) {
            const existing = streamingStates.get(key);
            if (existing) {
                existing.onUpdate = onUpdate || existing.onUpdate;
            }
            processStreaming(key, message);
            return;
        }
        
        // Initialize state
        const state = {
            stage: message._streamStage || 'pending',
            displayedLength: message._displayedSummary ? message._displayedSummary.length : 0,
            timer: null,
            chatId,
            messageIndex,
            onUpdate
        };
        
        streamingStates.set(key, state);
        
        // Start processing
        processStreaming(key, message);
    };
    
    const processStreaming = (key, message) => {
        const state = streamingStates.get(key);
        if (!state) return;
        
        if (message.isThinking) {
            state.stage = 'thinking';
            message._streamStage = 'thinking';
            if (state.onUpdate) state.onUpdate();
            return;
        }

        // thinking -> typing 过渡：当后端结果已返回（isThinking=false）时，直接进入打字
        if (state.stage === 'thinking' && message._shouldStream) {
            startTyping(key, message);
            return;
        }
        
        if (state.stage === 'pending' && message._shouldStream) {
            state.stage = 'thinking';
            message._streamStage = 'thinking';
            if (state.onUpdate) state.onUpdate();
            
            setTimeout(() => {
                const currentState = streamingStates.get(key);
                if (currentState && currentState.stage === 'thinking' && message.isThinking === false) {
                    startTyping(key, message);
                }
            }, 800);
        }
    };
    
    const startTyping = (key, message) => {
        const state = streamingStates.get(key);
        if (!state) return;
        
        state.stage = 'typing';
        message._streamStage = 'typing';
        if (state.onUpdate) state.onUpdate();
        
        const fullText = message.structuredData ? message.structuredData.summary : message.content;
        if (!fullText) {
            finishStreaming(key, message);
            return;
        }
        
        let currentIndex = state.displayedLength;
        const speed = 25; // ms per character
        
        state.timer = setInterval(() => {
            if (currentIndex < fullText.length) {
                currentIndex++;
                state.displayedLength = currentIndex;
                message._displayedSummary = fullText.slice(0, currentIndex);
                if (state.onUpdate) state.onUpdate();
            } else {
                finishStreaming(key, message);
            }
        }, speed);
    };
    
    const finishStreaming = (key, message) => {
        const state = streamingStates.get(key);
        if (!state) return;
        
        if (state.timer) {
            clearInterval(state.timer);
            state.timer = null;
        }
        
        state.stage = 'done';
        message._streamStage = 'done';
        message._shouldStream = false;
        if (state.onUpdate) state.onUpdate();
        
        streamingStates.delete(key);
    };
    
    const getState = (chatId, messageIndex) => {
        const key = getMessageKey(chatId, messageIndex);
        return streamingStates.get(key);
    };
    
    const stopStreaming = (chatId, messageIndex) => {
        const key = getMessageKey(chatId, messageIndex);
        const state = streamingStates.get(key);
        if (state && state.timer) {
            clearInterval(state.timer);
            state.timer = null;
        }
        streamingStates.delete(key);
    };
    
    const stopChatStreaming = (chatId) => {
        for (const [key, state] of streamingStates.entries()) {
            if (state.chatId === chatId) {
                if (state.timer) {
                    clearInterval(state.timer);
                }
                streamingStates.delete(key);
            }
        }
    };
    
    return {
        startStreaming,
        getState,
        stopStreaming,
        stopChatStreaming
    };
})();

export default StreamingManager;


