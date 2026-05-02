<script setup>
import { ref, watch, nextTick } from "vue";
import { storeToRefs } from "pinia";
import SendIcon from "../icons/SendIcon.vue";
import BotLogo from "../icons/BotLogo.vue";
import UserLogo from "../icons/UserLogo.vue";

import { useChatStore } from "../../store/chatStore";
import { useContentStore } from "../../store/contentStore";
import { useAuthStore } from "../../store/authStore";
import http from "../../router/axios";

const chatStore = useChatStore();
const contentStore = useContentStore();
const authStore = useAuthStore();
const { addChatData, addQueryData, sendAiMessage, clearAiHistory, saveChatLog } = chatStore;
const { createDashboard } = contentStore;
const { chatData, chatMode, isAiStreaming } = storeToRefs(chatStore);
const { editDashboard } = storeToRefs(contentStore);
const { user } = storeToRefs(authStore);

const userMessage = ref("");
const chatAreaRef = ref(null);
const isStickyOpen = ref(false);
const dashboardCreationLoading = ref(false);

const qaBtnHandler = async (text, relations) => {
	if (text === "建立儀表板") {
		if (dashboardCreationLoading.value === true) return;
		dashboardCreationLoading.value = true;
		// 確認個人儀表板是否超過20個
		const response = await http.get(`/dashboard/`);
		if (response.data?.data?.personal?.length > 20) {
			addChatData({
				role: "bot",
				content:
					"您的個人儀表板已超出限制 20 個，請先移除既有儀表板後，重新執行本功能！",
			});
			dashboardCreationLoading.value = false;
			return;
		}
		const components = Array.from(new Set(relations.map((r) => r.id))).map(
			(id) => ({ id }),
		);

		if (user.value.user_id) {
			editDashboard.value = {
				index: "",
				name: "推薦儀表板",
				icon: "star",
				components: components,
			};
			await createDashboard();
			saveChatLog("建立儀表板", "使用者成功建立儀表板!");
		} else {
			addChatData({
				role: "bot",
				content: "請先登入會員以使用此功能喔！",
			});
		}
		dashboardCreationLoading.value = false;
	}
};

const onAiTabClick = () => {
	if (!user.value.user_id) {
		addChatData({ role: 'bot', content: '請先登入會員以使用 AI 對話功能！' });
		return;
	}
	chatMode.value = 'ai';
};

const sendBtnHandler = (text) => {
	if (!text.trim()) return;
	if (chatMode.value === 'ai') {
		sendAiMessage(text);
	} else {
		addQueryData({ role: 'user', content: text });
	}
	userMessage.value = "";
};

const toggleSticky = () => {
	isStickyOpen.value = !isStickyOpen.value;
};

watch(
	chatData,
	async () => {
		await nextTick();
		const chat = chatAreaRef.value;
		if (!chat) return;
		chat.scrollTop = chat.scrollHeight - chat.clientHeight;
	},
	{ deep: true },
);
</script>

<template>
  <div class="chat-widget">
    <!-- 標題 -->
    <div class="header">
      <h3>臺北城市儀表板小幫手</h3>
      <div class="mode-tabs">
        <button
          :class="{ active: chatMode === 'search' }"
          @click="chatMode = 'search'"
        >
          搜尋組件
        </button>
        <button
          :class="{ active: chatMode === 'ai' }"
          @click="onAiTabClick"
        >
          AI 對話
        </button>
      </div>
    </div>

    <!-- 聊天區 -->
    <div
      ref="chatAreaRef"
      class="chat-area scrollbar-custom"
    >
      <!-- 置頂訊息 -->
      <div class="chat-message sticky-message">
        <div
          class="sticky-header"
          @click="toggleSticky"
        >
          <span>置頂公告：小幫手使用須知</span>
          <button class="toggle-btn">
            {{ isStickyOpen ? "-" : "+" }}
          </button>
        </div>
        <div
          v-show="isStickyOpen"
          class="sticky-body"
        >
          <span>
            <b>搜尋組件</b>：依輸入內容比對組件資料庫，回傳相似度高的組件清單，可一鍵建立個人儀表板。<br><br>
            <b>AI 對話</b>：透過 LLM 回答問題，支援多輪對話，可查詢資料庫即時資料。需登入後使用。
          </span>
        </div>
      </div>
      <div
        v-for="chat in chatData"
        :key="chat.id"
        class="message"
      >
        <!-- 機器人訊息 -->
        <div
          v-if="chat.role === 'bot'"
          class="bot"
        >
          <div class="avatar">
            <BotLogo />
          </div>
          <div class="content">
            <div
              v-if="chat.content || (isAiStreaming && chat === chatData[chatData.length - 1])"
              class="message--bubble"
            >
              <p>{{ chat.content }}<span
                v-if="isAiStreaming && chat === chatData[chatData.length - 1]"
                class="streaming-cursor"
              >▋</span></p>
            </div>
            <!-- 表格區 -->
            <div
              v-if="chat.relations"
              v-horizontal-wheel
              class="relation-area"
            >
              <table class="relation-table">
                <thead>
                  <tr>
                    <th>排名</th>
                    <th>城市名</th>
                    <th>組件名</th>
                    <th>關聯性</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(item, index) in chat.relations"
                    :key="index"
                  >
                    <td>{{ index + 1 }}</td>
                    <td>
                      {{
                        item.city === "taipei"
                          ? "臺北"
                          : "雙北"
                      }}
                    </td>
                    <td>{{ item.name }}</td>
                    <td>{{ item.score }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              v-if="chat.button"
              v-horizontal-wheel
              class="message--button scrollbar-x-hide"
            >
              <button
                v-for="btn in chat.button"
                :key="btn.id"
                @click="qaBtnHandler(btn.text, chat.relations)"
              >
                {{ btn.text }}
              </button>
            </div>
          </div>
        </div>
        <!-- 使用者訊息 -->
        <div
          v-else
          class="user"
        >
          <div class="avatar">
            <UserLogo />
          </div>
          <div
            v-if="chat.content"
            class="content"
          >
            <div class="message--bubble">
              <p>{{ chat.content }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 輸入區 -->
    <div class="input-area">
      <input
        v-model="userMessage"
        type="text"
        placeholder="輸入訊息..."
        @keyup.enter="sendBtnHandler(userMessage)"
      >
      <button @click="sendBtnHandler(userMessage)">
        <SendIcon />
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
/* === 變數設定 === */
$bg-dark: #090909;
$panel-bg: #494b4e;
$card-bg: #282a2c;
$border-color: #888787;
$input-bg: #d9d9d9;
$white: #ffffff;
$scroll-thumb-hover: #ababab;
$radius-10: 10px;
$radius-15: 15px;
$radius-20: 20px;

/* === Scrollbar === */
.scrollbar-x-hide {
	scrollbar-width: none;

	&::-webkit-scrollbar {
		display: none;
	}
}

.scrollbar-custom {
	&::-webkit-scrollbar {
		width: 2px;
		background: transparent;
	}

	&::-webkit-scrollbar-thumb {
		background: $white;
		border-radius: 8px;
	}

	&::-webkit-scrollbar-thumb:hover {
		background: $scroll-thumb-hover;
	}
}

/* === 主要樣式 === */
.chat-widget {
	width: 400px;
	border-radius: $radius-20;
	overflow: hidden;
	background: $bg-dark;
	border: 1px solid $border-color;
	display: flex;
	flex-direction: column;

	.header {
		padding: 1rem;
		background: $panel-bg;
		border-bottom: 3px solid $border-color;

		h3 {
			font-size: 18px;
			font-weight: 700;
			color: $white;
			margin: 0 0 0.75rem;
		}

		.mode-tabs {
			display: flex;
			gap: 0.5rem;

			button {
				flex: 1;
				padding: 0.35rem 0;
				border-radius: $radius-15;
				border: 1px solid $border-color;
				background: transparent;
				color: $white;
				font-size: 13px;
				cursor: pointer;
				transition: background 0.15s;

				&:hover {
					background: rgba(255, 255, 255, 0.1);
				}

				&.active {
					background: $white;
					color: $bg-dark;
					font-weight: 700;
					border-color: $white;
				}
			}
		}
	}

	.chat-area {
		flex: 1;
		margin: 0.25rem;
		padding: 0.75rem;
		overflow-y: auto;
		background: $bg-dark;

		.chat-message {
			padding: 4px 10px;
			margin: 0px 8px;
			border-radius: 8px;
			background-color: $bg-dark;
		}

		// 置頂訊息
		.sticky-message {
			border: 1px solid #ffffff;
			position: sticky;
			top: 0;
			z-index: 10;

			.sticky-header {
				display: flex;
				font-weight: bold;
				justify-content: space-between;
				align-items: center;
				cursor: pointer;
				padding: 8px 12px;
			}

			.sticky-body {
				padding: 8px 12px;
				font-weight: 400;
				font-size: 14px;
			}

			.toggle-btn {
				background: none;
				border: none;
				font-size: 14px;
				cursor: pointer;
				color: #ffffff;
			}
		}

		.message {
			padding: 8px;

			.bot,
			.user {
				display: flex;
				gap: 0.5rem;
				align-items: flex-start;

				&.user {
					flex-direction: row-reverse;
				}

				.avatar {
					width: 40px;
					height: 40px;
					display: flex;
					align-items: center;
					justify-content: center;
					flex-shrink: 0;

					svg {
						width: 100%;
						height: auto;
					}
				}

				.content {
					display: flex;
					flex-direction: column;
					gap: 0.5rem;

					.relation-area {
						width: 100%;
						display: flex;
						align-items: center;
						margin-top: 8px;
						margin-bottom: 8px;

						.relation-table {
							min-width: max-content;
							font-size: 13px;
						}

						.relation-table th,
						.relation-table td {
							border: 1px solid #ccc;
							text-align: left;
							padding: 0px 8px;
							line-height: 1.1;
							vertical-align: middle;
						}

						.relation-table td {
							height: 2.5rem;
						}

						.relation-table th {
							font-weight: bold;
							text-align: center;
						}
					}

					.message--bubble {
						border: 1px solid $white;
						border-radius: $radius-10;
						background: $card-bg;

						p {
							color: $white;
							white-space: pre-line;
							margin: 0;
							padding-top: 8px;
							padding-bottom: 8px;
							padding-left: 16px;
							padding-right: 16px;
							font-size: 16px;

							.streaming-cursor {
								display: inline-block;
								animation: blink 0.8s step-end infinite;
							}
						}
					}

					@keyframes blink {
						50% { opacity: 0; }
					}

					.message--button {
						display: flex;
						gap: 0.5rem;
						overflow-x: auto;

						button {
							flex-shrink: 0;
							background: $panel-bg;
							color: $white;
							font-size: 14px;
							padding: 0.5rem 1rem;
							border-radius: $radius-15;
							border: none;
							cursor: pointer;
							white-space: nowrap;

							&:hover {
								filter: brightness(0.5);
							}
						}
					}
				}
			}
		}
	}

	.input-area {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 1.5rem 1.125rem;
		background: $panel-bg;

		input[type="text"] {
			background: $white;
			height: 35px;
			width: 100%;
			border-radius: 20px;
			padding: 0 1rem;
			border: none;
			outline: none;
			color: black;
		}

		button {
			height: 35px;
			display: flex;
			align-items: center;
			justify-content: center;
			background: transparent;
			border: none;
			cursor: pointer;

			&:hover {
				filter: brightness(0.5);
			}
		}
	}
}
</style>
