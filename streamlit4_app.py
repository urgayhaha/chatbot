import streamlit as st
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical
import numpy as np
import random
from collections import deque
import time

st.set_page_config(page_title="Intrinsic Motivation Lab", page_icon="🧠", layout="wide")

# ==================== MODELS ====================
class FeatureEncoder(nn.Module):
    def __init__(self, state_dim, feature_dim=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, feature_dim),
            nn.ReLU()
        )
    def forward(self, x):
        return self.net(x)

class ForwardModel(nn.Module):
    def __init__(self, feature_dim, action_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(feature_dim + action_dim, 64),
            nn.ReLU(),
            nn.Linear(64, feature_dim)
        )
    def forward(self, feat, action_oh):
        return self.net(torch.cat([feat, action_oh], dim=-1))

class InverseModel(nn.Module):
    def __init__(self, feature_dim, action_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(feature_dim * 2, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )
    def forward(self, feat, next_feat):
        return self.net(torch.cat([feat, next_feat], dim=-1))

class ActorCritic(nn.Module):
    def __init__(self, feature_dim, action_dim):
        super().__init__()
        self.shared = nn.Sequential(nn.Linear(feature_dim, 64), nn.ReLU())
        self.actor = nn.Linear(64, action_dim)
        self.critic = nn.Linear(64, 1)
    def forward(self, feat):
        h = self.shared(feat)
        return self.actor(h), self.critic(h)

# ==================== AGENT ====================
class ICMAgent:
    def __init__(self, state_dim=6, action_dim=4, feature_dim=32, lr=1e-3):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.encoder = FeatureEncoder(state_dim, feature_dim)
        self.forward_m = ForwardModel(feature_dim, action_dim)
        self.inverse_m = InverseModel(feature_dim, action_dim)
        self.policy = ActorCritic(feature_dim, action_dim)
        params = list(self.encoder.parameters()) + list(self.forward_m.parameters()) + \
                 list(self.inverse_m.parameters()) + list(self.policy.parameters())
        self.opt = torch.optim.Adam(params, lr=lr)
        self.memory = deque(maxlen=2000)
        self.beta = 0.2
        self.eta = 1.0
        self.gamma = 0.95

    def onehot(self, a):
        return F.one_hot(a.long(), self.action_dim).float()

    def intrinsic_reward(self, s, a, ns):
        with torch.no_grad():
            f = self.encoder(s)
            nf = self.encoder(ns)
            pred = self.forward_m(f, self.onehot(a))
            err = ((pred - nf) ** 2).mean(dim=-1)
            return (self.eta * err).cpu().numpy()

    def store(self, s, a, r, ns, d):
        self.memory.append((s, a, r, ns, d))

    def update(self, bs=32):
        if len(self.memory) < bs:
            return None
        batch = random.sample(self.memory, bs)
        S = torch.FloatTensor(np.array([b[0] for b in batch]))
        A = torch.LongTensor([b[1] for b in batch])
        R = torch.FloatTensor([b[2] for b in batch])
        NS = torch.FloatTensor(np.array([b[3] for b in batch]))
        D = torch.FloatTensor([b[4] for b in batch])

        feat = self.encoder(S)
        nfeat = self.encoder(NS)
        a_oh = self.onehot(A)

        # ICM
        inv_logits = self.inverse_m(feat, nfeat)
        inv_loss = F.cross_entropy(inv_logits, A)
        pred_nf = self.forward_m(feat.detach(), a_oh)
        fwd_loss = F.mse_loss(pred_nf, nfeat.detach())
        icm_loss = (1 - self.beta) * fwd_loss + self.beta * inv_loss

        # Intrinsic + Policy
        with torch.no_grad():
            intr = torch.FloatTensor(self.intrinsic_reward(S, A, NS))
        total_r = R + intr

        logits, values = self.policy(feat.detach())
        dist = Categorical(logits=logits)
        logp = dist.log_prob(A)
        ent = dist.entropy().mean()

        with torch.no_grad():
            _, nv = self.policy(self.encoder(NS))
            targets = total_r + self.gamma * nv.squeeze() * (1 - D)
            adv = targets - values.squeeze()

        pol_loss = -(logp * adv.detach()).mean()
        val_loss = F.mse_loss(values.squeeze(), targets)

        loss = icm_loss + pol_loss + 0.5 * val_loss - 0.01 * ent
        self.opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(self.encoder.parameters()) + list(self.forward_m.parameters()) +
            list(self.inverse_m.parameters()) + list(self.policy.parameters()), 0.5)
        self.opt.step()
        return {"icm": icm_loss.item(), "fwd": fwd_loss.item(), "pol": pol_loss.item()}

def dummy_step(state_dim=6, action_dim=4):
    s = np.random.randn(state_dim).astype(np.float32) * 0.5
    a = np.random.randint(0, action_dim)
    ns = s.copy()
    ns[a % state_dim] += np.random.uniform(0.3, 0.8)
    ns += np.random.randn(state_dim).astype(np.float32) * 0.05
    r = float(np.random.randn() * 0.05)
    d = float(np.random.rand() < 0.03)
    return s, a, r, ns, d

# ==================== STREAMLIT ====================
if "agent" not in st.session_state:
    st.session_state.agent = ICMAgent()
if "logs" not in st.session_state:
    st.session_state.logs = []
if "step_count" not in st.session_state:
    st.session_state.step_count = 0
if "running" not in st.session_state:
    st.session_state.running = False

agent = st.session_state.agent

st.title("🧠 Intrinsic Motivation Lab (ICM)")
st.caption("Forward Model + Inverse Model + Prediction Error Reward + Actor-Critic")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🟢 Bắt đầu huấn luyện" if not st.session_state.running else "⏸️ Tạm dừng", use_container_width=True):
        st.session_state.running = not st.session_state.running
        st.rerun()
with col2:
    if st.button("🔄 Reset Agent", use_container_width=True):
        st.session_state.agent = ICMAgent()
        st.session_state.logs = []
        st.session_state.step_count = 0
        st.session_state.running = False
        st.rerun()
with col3:
    st.metric("Steps", st.session_state.step_count)

st.divider()

# Hiển thị kiến trúc
with st.expander("📐 Kiến trúc", expanded=False):
    st.markdown("""
