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
const { addChatData, addQueryData, sendAiMessage, saveChatLog } = chatStore;
const { createDashboard } = contentStore;
const { chatData, chatMode, isAiStreaming } = storeToRefs(chatStore);
const { editDashboard } = storeToRefs(contentStore);
const { user } = storeToRefs(authStore);

const emit = defineEmits(["close"]);

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
		addChatData({
			role: "bot",
			content: "請先登入會員以使用 AI 對話功能！",
		});
		return;
	}
	chatMode.value = "ai";
};

const sendBtnHandler = (text) => {
	if (!text.trim()) return;
	if (chatMode.value === "ai") {
		sendAiMessage(text);
	} else {
		addQueryData({ role: "user", content: text });
	}
	userMessage.value = "";
};

const toggleSticky = () => {
	isStickyOpen.value = !isStickyOpen.value;
};

const closeChat = () => {
	emit("close");
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
	<section class="chat-widget" aria-label="臺北城市儀表板小幫手">
		<header class="chat-header">
			<div class="chat-header__top">
				<div>
					<h3>臺北城市儀表板小幫手 2.0</h3>
				</div>
				<div class="header-actions">
					<button
						type="button"
						class="icon-btn"
						aria-label="關閉小幫手"
						@click="closeChat"
					>
						<span aria-hidden="true">×</span>
					</button>
				</div>
			</div>
			<div class="mode-tabs" role="tablist" aria-label="對話模式">
				<button
					type="button"
					role="tab"
					:aria-selected="chatMode === 'search'"
					:class="{ active: chatMode === 'search' }"
					@click="chatMode = 'search'"
				>
					搜尋組件
				</button>
				<button
					type="button"
					role="tab"
					:aria-selected="chatMode === 'ai'"
					:class="{ active: chatMode === 'ai' }"
					@click="onAiTabClick"
				>
					AI 對話
				</button>
			</div>
		</header>

		<div ref="chatAreaRef" class="chat-area scrollbar-custom">
			<article class="sticky-message" :class="{ open: isStickyOpen }">
				<button
					type="button"
					class="sticky-header"
					:aria-expanded="isStickyOpen"
					@click="toggleSticky"
				>
					<span>操作提示</span>
					<span class="toggle-icon" aria-hidden="true">
						{{ isStickyOpen ? "−" : "+" }}
					</span>
				</button>
				<div v-show="isStickyOpen" class="sticky-body">
					<p>
						<b>搜尋組件：</b>可依主題建立推薦清單
						<br />
						<b>AI 對話：</b> 可查詢即時城市資料，需登入後使用
					</p>
				</div>
			</article>

			<div
				v-for="chat in chatData"
				:key="chat.id"
				class="message"
				:class="chat.role === 'bot' ? 'message--bot' : 'message--user'"
			>
				<div v-if="chat.role === 'bot'" class="message-row bot">
					<div class="avatar" aria-hidden="true">
						<BotLogo />
					</div>
					<div class="content">
						<div
							v-if="
								chat.content ||
								(isAiStreaming &&
									chat === chatData[chatData.length - 1])
							"
							class="message-bubble"
						>
							<p>
								{{ chat.content
								}}<span
									v-if="
										isAiStreaming &&
										chat === chatData[chatData.length - 1]
									"
									class="streaming-cursor"
									aria-hidden="true"
									>▋</span
								>
							</p>
						</div>
						<div
							v-if="chat.relations"
							v-horizontal-wheel
							class="relation-area"
						>
							<table class="relation-table">
								<thead>
									<tr>
										<th>排名</th>
										<th>城市</th>
										<th>組件名稱</th>
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
							class="message-actions scrollbar-x-hide"
						>
							<button
								v-for="btn in chat.button"
								:key="btn.id"
								type="button"
								:disabled="dashboardCreationLoading"
								@click="qaBtnHandler(btn.text, chat.relations)"
							>
								{{
									dashboardCreationLoading
										? "建立中..."
										: btn.text
								}}
							</button>
						</div>
					</div>
				</div>
				<div v-else class="message-row user">
					<div class="avatar" aria-hidden="true">
						<UserLogo />
					</div>
					<div v-if="chat.content" class="content">
						<div class="message-bubble">
							<p>{{ chat.content }}</p>
						</div>
					</div>
				</div>
			</div>
		</div>

		<form class="input-area" @submit.prevent="sendBtnHandler(userMessage)">
			<label class="sr-only" for="chatbot-message-input">輸入訊息</label>
			<input
				id="chatbot-message-input"
				v-model="userMessage"
				type="text"
				:placeholder="
					chatMode === 'ai'
						? '詢問即時城市資料...'
						: '輸入想看的城市主題...'
				"
				autocomplete="off"
			/>
			<button
				type="submit"
				:disabled="isAiStreaming || !userMessage.trim()"
				aria-label="送出訊息"
			>
				<SendIcon />
			</button>
		</form>
	</section>
</template>

<style lang="scss" scoped>
$bg-dark: #090909;
$surface: #111315;
$surface-soft: #1c2024;
$panel-bg: #282a2c;
$border-color: #494b4e;
$border-bright: rgba(255, 255, 255, 0.18);
$text: #f4f7fb;
$text-muted: #aeb6c2;
$highlight: #5a9cf8;
$highlight-strong: #83b9ff;
$success: #74d3a5;
$shadow: 0 24px 80px rgba(0, 0, 0, 0.48);
$radius-panel: 18px;
$radius-card: 12px;
$radius-control: 999px;

.sr-only {
	position: absolute;
	width: 1px;
	height: 1px;
	padding: 0;
	margin: -1px;
	overflow: hidden;
	clip: rect(0, 0, 0, 0);
	white-space: nowrap;
	border: 0;
}

.scrollbar-x-hide {
	scrollbar-width: none;

	&::-webkit-scrollbar {
		display: none;
	}
}

.scrollbar-custom {
	&::-webkit-scrollbar {
		width: 6px;
		background: transparent;
	}

	&::-webkit-scrollbar-thumb {
		background: rgba(255, 255, 255, 0.28);
		border-radius: 8px;
	}

	&::-webkit-scrollbar-thumb:hover {
		background: rgba(255, 255, 255, 0.5);
	}
}

.chat-widget {
	width: 400px;
	height: 100%;
	border-radius: $radius-panel;
	overflow: hidden;
	background:
		linear-gradient(
			180deg,
			rgba(90, 156, 248, 0.1) 0%,
			rgba(9, 9, 9, 0) 30%
		),
		$bg-dark;
	border: 1px solid $border-bright;
	box-shadow: $shadow;
	display: flex;
	flex-direction: column;
	backdrop-filter: blur(16px);

	.chat-header {
		padding: 18px 18px 14px;
		background:
			linear-gradient(135deg, rgba(90, 156, 248, 0.16), transparent 55%),
			$surface;
		border-bottom: 1px solid $border-color;

		&__top {
			display: flex;
			align-items: flex-start;
			justify-content: space-between;
			gap: 14px;
			margin-bottom: 14px;
		}

		.eyebrow {
			margin-bottom: 5px;
			color: $highlight-strong;
			font-size: 11px;
			font-weight: 700;
			line-height: 1.2;
			text-transform: uppercase;
		}

		h3 {
			margin: 0;
			color: $text;
			font-size: 18px;
			font-weight: 800;
			line-height: 1.35;
		}

		.header-actions {
			display: flex;
			align-items: center;
			gap: 8px;
			flex-shrink: 0;
		}

		.status-pill {
			display: inline-flex;
			align-items: center;
			gap: 6px;
			min-height: 28px;
			padding: 0 10px;
			border: 1px solid rgba(116, 211, 165, 0.24);
			border-radius: $radius-control;
			background: rgba(116, 211, 165, 0.1);
			color: $success;
			font-size: 12px;
			font-weight: 700;
			line-height: 1;

			&::before {
				content: "";
				width: 6px;
				height: 6px;
				border-radius: 50%;
				background: currentColor;
				box-shadow: 0 0 12px currentColor;
			}

			&.streaming {
				border-color: rgba(90, 156, 248, 0.3);
				background: rgba(90, 156, 248, 0.12);
				color: $highlight-strong;
			}
		}

		.icon-btn {
			width: 32px;
			height: 32px;
			display: inline-flex;
			align-items: center;
			justify-content: center;
			border: 1px solid $border-bright;
			border-radius: 50%;
			background: rgba(255, 255, 255, 0.04);
			color: $text;
			transition:
				background 0.18s ease,
				border-color 0.18s ease,
				transform 0.18s ease;

			span {
				color: inherit;
				font-size: 22px;
				line-height: 1;
				transform: translateY(-1px);
			}

			&:hover,
			&:focus-visible {
				background: rgba(255, 255, 255, 0.1);
				border-color: rgba(255, 255, 255, 0.35);
			}

			&:active {
				transform: scale(0.96);
			}
		}

		.mode-tabs {
			display: grid;
			grid-template-columns: repeat(2, minmax(0, 1fr));
			gap: 6px;
			padding: 4px;
			border: 1px solid rgba(255, 255, 255, 0.1);
			border-radius: $radius-control;
			background: rgba(0, 0, 0, 0.28);

			button {
				min-height: 38px;
				border-radius: $radius-control;
				color: $text-muted;
				font-size: 13px;
				font-weight: 700;
				transition:
					background 0.18s ease,
					color 0.18s ease,
					box-shadow 0.18s ease;

				&:hover,
				&:focus-visible {
					color: $text;
					background: rgba(255, 255, 255, 0.06);
				}

				&.active {
					background: linear-gradient(135deg, $highlight, #7bd2ff);
					color: #07111f;
					box-shadow: 0 8px 24px rgba(90, 156, 248, 0.25);
				}
			}
		}
	}

	.chat-area {
		flex: 1;
		min-height: 0;
		padding: 14px 14px 18px;
		overflow-y: auto;
		background:
			linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 22%),
			$bg-dark;

		.sticky-message {
			position: sticky;
			top: 0;
			z-index: 10;
			margin-bottom: 10px;
			border: 1px solid rgba(90, 156, 248, 0.22);
			border-radius: $radius-card;
			background: rgba(17, 19, 21, 0.92);
			box-shadow: 0 12px 30px rgba(0, 0, 0, 0.28);

			.sticky-header {
				display: flex;
				align-items: center;
				justify-content: space-between;
				width: 100%;
				min-height: 42px;
				padding: 0 12px;
				color: $text;
				font-size: 13px;
				font-weight: 800;
				text-align: left;
			}

			.sticky-body {
				padding: 0 12px 12px;

				p {
					margin: 0;
					color: $text-muted;
					font-size: 13px;
					line-height: 1.55;

					b {
						color: $text;
					}
				}
			}

			.toggle-icon {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				width: 24px;
				height: 24px;
				border-radius: 50%;
				background: rgba(255, 255, 255, 0.07);
				color: $highlight-strong;
				font-size: 18px;
				line-height: 1;
			}
		}

		.message {
			padding: 7px 0;

			.message-row {
				display: flex;
				align-items: flex-start;
				gap: 10px;

				&.user {
					flex-direction: row-reverse;
				}

				.avatar {
					width: 34px;
					height: 34px;
					display: flex;
					align-items: center;
					justify-content: center;
					flex-shrink: 0;
					border-radius: 50%;
					background: rgba(255, 255, 255, 0.05);
					box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08);

					svg {
						width: 34px;
						height: 34px;
					}
				}

				.content {
					max-width: calc(100% - 48px);
					display: flex;
					flex-direction: column;
					gap: 8px;

					.relation-area {
						max-width: 100%;
						overflow-x: auto;
						border: 1px solid rgba(255, 255, 255, 0.1);
						border-radius: $radius-card;
						background: rgba(255, 255, 255, 0.03);

						.relation-table {
							min-width: max-content;
							width: 100%;
							font-size: 13px;
							border: 0;
							border-radius: 0;
							overflow: visible;
						}

						.relation-table th,
						.relation-table td {
							text-align: left;
							padding: 10px 12px;
							border: 0;
							border-bottom: 1px solid rgba(255, 255, 255, 0.08);
							vertical-align: middle;
							line-height: 1.35;
							color: $text;
						}

						.relation-table th {
							height: auto;
							background: rgba(90, 156, 248, 0.14);
							color: $highlight-strong;
							font-weight: 800;
						}

						.relation-table td {
							height: auto;
							background: transparent;
						}
					}

					.message-actions {
						display: flex;
						gap: 8px;
						overflow-x: auto;

						button {
							flex-shrink: 0;
							min-height: 36px;
							padding: 0 14px;
							border: 1px solid rgba(90, 156, 248, 0.34);
							border-radius: $radius-control;
							background: rgba(90, 156, 248, 0.16);
							color: $highlight-strong;
							font-size: 14px;
							font-weight: 800;
							white-space: nowrap;
							transition:
								background 0.18s ease,
								color 0.18s ease,
								transform 0.18s ease;

							&:hover,
							&:focus-visible {
								background: rgba(90, 156, 248, 0.24);
								color: $text;
							}

							&:active {
								transform: scale(0.98);
							}

							&:disabled {
								opacity: 0.55;
								cursor: not-allowed;
							}
						}
					}
				}
			}

			.message-bubble {
				border: 1px solid rgba(255, 255, 255, 0.1);
				border-radius: $radius-card;
				background: $surface-soft;
				box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);

				p {
					margin: 0;
					padding: 11px 14px;
					color: $text;
					font-size: 15px;
					line-height: 1.62;
					white-space: pre-line;

					.streaming-cursor {
						display: inline-block;
						color: $highlight-strong;
						animation: blink 0.8s step-end infinite;
					}
				}
			}

			&.message--user {
				.message-bubble {
					border-color: rgba(90, 156, 248, 0.38);
					background: linear-gradient(135deg, #2364b5, #1c4d8d);

					p {
						color: #f8fbff;
					}
				}
			}
		}
	}

	.input-area {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 14px 16px 16px;
		border-top: 1px solid $border-color;
		background: rgba(17, 19, 21, 0.96);

		input[type="text"] {
			height: 46px;
			width: 100%;
			padding: 0 16px;
			border: 1px solid rgba(255, 255, 255, 0.12);
			border-radius: $radius-control;
			background: rgba(255, 255, 255, 0.07);
			color: $text;
			font-size: 15px;
			transition:
				border-color 0.18s ease,
				box-shadow 0.18s ease,
				background 0.18s ease;

			&::placeholder {
				color: rgba(244, 247, 251, 0.52);
			}

			&:focus {
				border-color: rgba(90, 156, 248, 0.8);
				background: rgba(255, 255, 255, 0.09);
				box-shadow: 0 0 0 3px rgba(90, 156, 248, 0.16);
			}
		}

		button {
			width: 46px;
			height: 46px;
			display: flex;
			align-items: center;
			justify-content: center;
			flex-shrink: 0;
			border-radius: 50%;
			background: linear-gradient(135deg, $highlight, #77d6ff);
			box-shadow: 0 10px 28px rgba(90, 156, 248, 0.3);
			transition:
				filter 0.18s ease,
				transform 0.18s ease,
				opacity 0.18s ease;

			&:hover,
			&:focus-visible {
				filter: brightness(1.08);
			}

			&:active {
				transform: scale(0.96);
			}

			&:disabled {
				opacity: 0.42;
				cursor: not-allowed;
				filter: grayscale(0.35);
			}

			svg {
				width: 38px;
				height: 38px;
			}
		}
	}
}

@keyframes blink {
	50% {
		opacity: 0;
	}
}

@media (prefers-reduced-motion: reduce) {
	.chat-widget *,
	.chat-widget *::before,
	.chat-widget *::after {
		animation-duration: 0.01ms !important;
		animation-iteration-count: 1 !important;
		transition-duration: 0.01ms !important;
	}
}
</style>
