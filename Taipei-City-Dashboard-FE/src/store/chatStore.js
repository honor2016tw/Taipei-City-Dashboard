import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import http from "../router/axios";
import { useAuthStore } from "./authStore";

export const useChatStore = defineStore('chat', () => {
  	// 預設訊息
  	const defaultChatData = [
    	{
      		id: 1,
      		role: 'bot',
	  		isDefault: true,
      		content:
        	'您好，我是【臺北城市儀表板】小幫手，很高興為您服務！\n 您可以： \n\n • 點擊左側既有的儀表板主題，快速查看各主題內容 \n • 輸入您感興趣的主題描述，我會自動為您組建最適合的儀表板 \n\n 如果有想了解的內容，歡迎直接告訴我，我會盡力協助！\n\n 📩 聯絡信箱：tuic@gov.taipei \n 🏢 臺北大數據中心 \n\n',
    	},
  	];

	const recommendComponents = ref(null)

	const chatMode = ref('search') // 'search' | 'ai'
	const aiMessages = ref([])
	const aiSessionId = ref(`sess_${Date.now()}`)
	const isAiStreaming = ref(false)

  	// 從 sessionStorage 讀取
  	const savedChatData = JSON.parse(sessionStorage.getItem('chatData')) || [];

  	// 拼接預設訊息 + sessionStorage 的聊天紀錄
  	const chatData = ref([...defaultChatData, ...savedChatData]);

  	// 監聽 chatData 的變化，自動同步到 sessionStorage
  	watch(
    	chatData,
    	(newVal) => {
      	// 只存使用者與機器人的聊天訊息，不存重複的預設訊息
      	const userBotMessages = newVal.filter((item) => !item.isDefault)
      	sessionStorage.setItem('chatData', JSON.stringify(userBotMessages))
    	},
    	{ deep: true }
  	);

  	const addChatData = (newChatData) => {
    	chatData.value.push({ id: chatData.value.length + 1, isDefault: false, ...newChatData });
  	};

  	const addQueryData = async (newChatData) => {

    	chatData.value.push({ id: chatData.value.length + 1, isDefault: false, ...newChatData });

		recommendComponents.value = [];
		let topK = null;

		try {
			const response = await http.post(
  				"/vector/component",
  				new URLSearchParams({
    				query: newChatData.content,
    				limit: 10,
    				score: 0.8,
  				}),
  				{
    				headers: {
      					"Content-Type": "application/x-www-form-urlencoded",
    				},
  				}
			);
			if (response.data?.data?.length > 0) {
				recommendComponents.value = response.data.data;
			}

			// 去除重複項目存到 result
			const result = Array.from(
  				recommendComponents.value.reduce((map, item) => {
    				const key = item.index
    				const exist = map.get(key)

    				// 如果還沒放過，直接放
    				if (!exist) {
      					map.set(key, item)
      					return map
    				}

    				// 如果已存在，但現在的是 metrotaipei，就覆蓋
    				if (item.city === 'metrotaipei') {
      					map.set(key, item)
    				}

    				return map
  				}, new Map()).values()
			)
			// 把 result 蓋回去 recommendComponents
			recommendComponents.value = result

		} catch (error) { 
			console.error("VectorAnalysisError :", error);
		}

		if (recommendComponents.value && recommendComponents.value?.length > 0) {
			topK = [...recommendComponents.value].sort((a, b) => b.score - a.score);
			chatData.value.push({ id: chatData.value.length + 1, role: 'bot', isDefault: false, button: [{ id:1, text:'建立儀表板' }], content: `您好 😊 \n 以下是根據您的問題，自動為您推薦的「組件清單」。您可以將這些組件整批加入「個人儀表板」，方便日後快速查看與使用。\n`, relations: topK });
			chatData.value.push({ id: chatData.value.length + 1, role: 'bot', isDefault: false, content: `若您有任何新的查詢或想深入探索的內容，都可以隨時在對話框告訴我～\n 我很樂意再協助您 💬✨` });
		} else {
			chatData.value.push({ id: chatData.value.length + 1, role: 'bot', isDefault: false, content: `很抱歉，您提供的描述沒有相似組件，請繼續提問 ! ` });
		}

		// 分析結束後紀錄問答log
		saveChatLog(newChatData.content, recommendComponents.value);
  	};

	const sendAiMessage = async (text) => {
		if (isAiStreaming.value || !text.trim()) return

		addChatData({ role: 'user', content: text })
		aiMessages.value.push({ role: 'user', content: text })

		const placeholderIdx = chatData.value.length
		chatData.value.push({ id: placeholderIdx + 1, role: 'bot', isDefault: false, content: '' })

		isAiStreaming.value = true

		try {
			const authStore = useAuthStore()
			const res = await fetch(`${import.meta.env.VITE_API_URL}/ai/chat/twai`, {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${authStore.token}`,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					messages: aiMessages.value,
					session_id: aiSessionId.value,
					stream: true,
				}),
			})

			if (!res.ok) {
				if (res.status === 401) authStore.handleLogout()
				chatData.value[placeholderIdx].content = `錯誤 ${res.status}，請稍後再試。`
				return
			}

			const reader = res.body.getReader()
			const decoder = new TextDecoder()
			let fullContent = ''
			let buffer = ''

			while (true) {
				const { done, value } = await reader.read()
				if (done) break
				buffer += decoder.decode(value, { stream: true })
				const lines = buffer.split('\n')
				buffer = lines.pop() // 保留未完成的行

				for (const line of lines) {
					if (!line.startsWith('data:')) continue
					const raw = line.slice(5).trim()
					if (raw === '[DONE]') continue
					try {
						const parsed = JSON.parse(raw)
						const delta = parsed.generated_text ?? parsed.choices?.[0]?.delta?.content ?? ''
						fullContent += delta
						chatData.value[placeholderIdx].content = fullContent
					} catch {}
				}
			}

			if (!fullContent) chatData.value[placeholderIdx].content = '（無回應）'
			aiMessages.value.push({ role: 'assistant', content: fullContent })

		} catch (err) {
			chatData.value[placeholderIdx].content = '發生網路錯誤，請稍後再試。'
			console.error('AI chat error:', err)
		} finally {
			isAiStreaming.value = false
		}
	}

	const clearAiHistory = () => {
		aiMessages.value = []
		aiSessionId.value = `sess_${Date.now()}`
	}

	const saveChatLog = async(question, answer) => {
		try {
        	const formData = new FormData();
        	const d = new Date();
        	const todayId =
          		d.getFullYear() +
          		String(d.getMonth() + 1).padStart(2, "0") +
          		String(d.getDate()).padStart(2, "0");

        	formData.append("session", "session_" + todayId);
        	formData.append("question", question);
        	formData.append("answer", JSON.stringify(answer));

        	await http.post("/chatlog/", formData, {
          		headers: {
            		"Content-Type": "multipart/form-data",
          		},
        	});
      	} catch (error) {
        	console.error("saveChatLog error:", error);
      	}
	};

	return { chatData, chatMode, aiMessages, aiSessionId, isAiStreaming, addChatData, addQueryData, sendAiMessage, clearAiHistory, saveChatLog }
})
