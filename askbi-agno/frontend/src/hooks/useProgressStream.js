/**
 * useProgressStream — SSE 流式进度 hook
 *
 * 通过 fetch + ReadableStream 消费后端 SSE /stream 端点，
 * 实时解析 stage 事件并返回 stages 数组。
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { withBase } from '../services/api';

/**
 * @param {string|null} chatid   会话 ID，为 null 时不连接
 * @param {string}      mode     'general' | 'bi' | 'excel' | 'team'，决定请求路径
 * @param {object}      opts     可选参数，team 模式需传 { teamId }
 * @returns {{ stages: Array, isDone: boolean, error: string|null, start: () => void, stop: () => void }}
 */
export default function useProgressStream(chatid, mode = 'bi', opts = {}) {
    const [stages, setStages] = useState([]);
    const [isDone, setIsDone] = useState(false);
    const [error, setError] = useState(null);

    const abortRef = useRef(null);

    const start = useCallback(() => {
        if (!chatid) return;
        // 重置状态
        setStages([]);
        setIsDone(false);
        setError(null);

        const token = localStorage.getItem('askbi_token') || '';
        let url;
        if (mode === 'excel') {
            url = withBase(`/excel/stream?chatid=${encodeURIComponent(chatid)}&token=${encodeURIComponent(token)}`);
        } else if (mode === 'team' && opts.teamId) {
            url = withBase(`/teams/${opts.teamId}/stream?chatid=${encodeURIComponent(chatid)}&token=${encodeURIComponent(token)}`);
        } else if (mode === 'general') {
            url = withBase(`/chat/stream?chatid=${encodeURIComponent(chatid)}&token=${encodeURIComponent(token)}`);
        } else {
            url = withBase(`/stream?chatid=${encodeURIComponent(chatid)}&token=${encodeURIComponent(token)}`);
        }

        const controller = new AbortController();
        abortRef.current = controller;

        (async () => {
            try {
                const resp = await fetch(url, { signal: controller.signal });
                if (!resp.ok || !resp.body) {
                    setError(`SSE 连接失败: ${resp.status}`);
                    setIsDone(true);
                    return;
                }

                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || ''; // 最后一段可能不完整

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        const payload = line.slice(6).trim();
                        if (!payload) continue;
                        try {
                            const event = JSON.parse(payload);
                            if (event.type === 'stage') {
                                setStages(prev => [...prev, event.data]);
                            } else if (event.type === 'text') {
                                setStages(prev => [...prev, { event: 'log', message: { stage: 'unknown', status: 'running', message: event.data } }]);
                            } else if (event.type === 'done') {
                                setIsDone(true);
                            }
                            // heartbeat 忽略
                        } catch {
                            // JSON 解析失败，跳过
                        }
                    }
                }

                // 流正常结束
                setIsDone(true);
            } catch (e) {
                if (e.name !== 'AbortError') {
                    setError(e.message);
                    setIsDone(true);
                }
            }
        })();
    }, [chatid, mode, opts.teamId]);

    const stop = useCallback(() => {
        if (abortRef.current) {
            abortRef.current.abort();
            abortRef.current = null;
        }
    }, []);

    useEffect(() => {
        if (!chatid) return undefined;
        start();
        return () => stop();
    }, [chatid, start, stop]);

    // 组件卸载时自动断开
    useEffect(() => () => {
        if (abortRef.current) abortRef.current.abort();
    }, []);

    return { stages, isDone, error, start, stop };
}
