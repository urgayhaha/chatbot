```python
import streamlit as st
import random
import matplotlib.pyplot as plt
import numpy as np
from streamlit_autorefresh import st_autorefresh   # pip install streamlit-autorefresh

# ------------------- Cấu hình -------------------
WIDTH, HEIGHT = 20, 20          # số ô (cột x hàng)
FPS = 8                         # khung/giây
# -------------------------------------------------

# ---------- Khởi tạo trạng thái ----------
def init_game():
    """Thiết lập lại toàn bộ trạng thái của trò chơi."""
    st.session_state.snake = [(WIDTH // 2, HEIGHT // 2)]   # đầu rắn ở cuối list
    st.session_state.direction = "RIGHT"
    st.session_state.food = (
        random.randint(0, WIDTH - 1),
        random.randint(0, HEIGHT - 1),
    )
    st.session_state.score = 0
    st.session_state.game_over = False
    st.session_state.playing = False   # False → chưa bắt đầu

# Nếu chưa có trạng thái nào, khởi tạo lần đầu
if "snake" not in st.session_state:
    init_game()
# ---------------------------------------------------------

# ---------- Di chuyển rắn ----------
def move_snake():
    """Thực hiện một bước di chuyển dựa trên hướng hiện tại."""
    head_x, head_y = st.session_state.snake[-1]

    if st.session_state.direction == "UP":
        head_y -= 1
    elif st.session_state.direction == "DOWN":
        head_y += 1
    elif st.session_state.direction == "LEFT":
        head_x -= 1
    elif st.session_state.direction == "RIGHT":
        head_x += 1

    # Vòng quanh biên (torus)
    new_head = (head_x % WIDTH, head_y % HEIGHT)

    # Va chạm thân → Game Over
    if new_head in st.session_state.snake:
        st.session_state.game_over = True
        st.session_state.playing = False
        return

    st.session_state.snake.append(new_head)

    # Kiểm tra ăn thức ăn
    if new_head == st.session_state.food:
        st.session_state.score += 1
        # Sinh thức ăn mới ở vị trí không trùng rắn
        while True:
            new_food = (
                random.randint(0, WIDTH - 1),
                random.randint(0, HEIGHT - 1),
            )
            if new_food not in st.session_state.snake:
                st.session_state.food = new_food
                break
    else:
        # Không ăn → bỏ đuôi
        st.session_state.snake.pop(0)
# ---------------------------------------------------------

# ---------- Vẽ màn hình ----------
def draw():
    """Vẽ lưới, rắn và thức ăn bằng matplotlib."""
    grid = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

    # Rắn – màu xanh lá
    for x, y in st.session_state.snake:
        grid[y, x] = (0, 255, 0)

    # Thức ăn – màu đỏ
    fx, fy = st.session_state.food
    grid[fy, fx] = (255, 0, 0)

    fig, ax = plt.subplots(figsize=(WIDTH, HEIGHT))
    ax.imshow(grid, interpolation="none")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"Score: {st.session_state.score}", fontsize=14)
    st.pyplot(fig)
# ---------------------------------------------------------

# ---------- Điều khiển hướng ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("↑"):
        if st.session_state.direction != "DOWN":
            st.session_state.direction = "UP"
    if st.button("←"):
        if st.session_state.direction != "RIGHT":
            st.session_state.direction = "LEFT"
    if st.button("→"):
        if st.session_state.direction != "LEFT":
            st.session_state.direction = "RIGHT"
    if st.button("↓"):
        if st.session_state.direction != "UP":
            st.session_state.direction = "DOWN"

# ---------- Nút Start / Restart ----------
if st.session_state.game_over:
    st.error(f"💀 Game Over!  Điểm: {st.session_state.score}")
    if st.button("Chơi lại"):
        init_game()
        st.rerun()          # dùng API mới, không còn experimental
else:
    if not st.session_state.playing:
        if st.button("Start"):
            st.session_state.playing = True
    else:
        if st.button("Pause"):
            st.session_state.playing = False
# ---------------------------------------------------------

# ---------- Vòng game (tự refresh) ----------
if st.session_state.playing and not st.session_state.game_over:
    move_snake()                                   # một bước mỗi lần rerun
    st_autorefresh(
        interval=1000 // FPS,                     # tự reload sau 1/FPS giây
        limit=None,
        key="game_loop"
    )
# ---------------------------------------------------------

# ---------- Vẽ cuối cùng ----------
draw()
```
