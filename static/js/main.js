const socket = io();
let myPlayerNum = -1;

const allScreens = document.querySelectorAll('.screen');
const startScreen = document.getElementById('start-screen');
const waitingScreen = document.getElementById('waiting-screen');
const gameScreen = document.getElementById('game-screen');
const roundResultScreen = document.getElementById('round-result-screen');
const gameOverScreen = document.getElementById('game-over-screen');

const waitingStatus = document.getElementById('waiting-status');
const gameInfoDiv = document.getElementById('game-info');
const myHandDiv = document.getElementById('player-hand');
const boardHandDiv = document.getElementById('board-hand');
const statusTbody = document.getElementById('player-status-tbody');
const logList = document.getElementById('game-log-list');
const playButton = document.getElementById('play-button');
const passButton = document.getElementById('pass-button');
const startGameButton = document.getElementById('start-game-button');
const numPlayersSelect = document.getElementById('num-players-select');
const playAgainButton = document.getElementById('play-again-button');
const playSound = document.getElementById('play-sound');

new Sortable(myHandDiv, { animation: 150, ghostClass: 'sortable-ghost' });

function showScreen(screenId) {
    allScreens.forEach(screen => {
        if (screen.id === screenId) {
            screen.classList.add('active');
        } else {
            screen.classList.remove('active');
        }
    });
}

startGameButton.addEventListener('click', () => {
    const numPlayers = numPlayersSelect.value;
    socket.emit('request_start_game', { 'num_players': numPlayers });
});

playAgainButton.addEventListener('click', () => {
    socket.emit('request_new_game');
});

socket.on('connect', () => console.log('✅ Connected!'));
socket.on('player_assigned', (data) => { myPlayerNum = data.player_num; });
socket.on('waiting_for_players', (data) => {
    showScreen('waiting-screen');
    waitingStatus.innerText = `(${data.current} / ${data.needed} 명)`;
});
socket.on('game_update', redrawGame);
socket.on('game_started', (gameState) => {
    showScreen('game-screen');
    redrawGame(gameState);
});
socket.on('error_message', (data) => alert(`오류: ${data.message}`));
socket.on('round_result', (data) => {
    document.getElementById('round-winner-text').innerText = `라운드 승자: 플레이어 ${data.winner}`;
    document.getElementById('round-payments-text').innerHTML = '<strong>정산 결과:</strong>\n' + data.payments.join('\n');
    document.getElementById('round-money-status-text').innerHTML = '\n<strong>현재 보유 금액:</strong>\n' + data.money_status.map((m, i) => `플레이어 ${i+1}: ${m}원`).join('\n');
    showScreen('round-result-screen');
    setTimeout(() => {
        if (!gameOverScreen.classList.contains('active')) {
            showScreen('game-screen');
        }
    }, 5000);
});
socket.on('game_over', (data) => {
    document.getElementById('final-rankings-text').innerHTML = '<strong>최종 순위:</strong>\n' + data.rankings.join('\n');
    const bankruptText = document.getElementById('bankrupt-players-text');
    if(data.bankrupt && data.bankrupt.length > 0) {
        bankruptText.innerText = "파산: 플레이어 " + data.bankrupt.join(', ');
    } else {
        bankruptText.innerText = "";
    }
    showScreen('game-over-screen');
});
socket.on('show_lobby', () => {
    showScreen('start-screen');
});
socket.on('player_left', (data) => {
    alert(`플레이어 ${data.player_num}의 접속이 끊어져 게임이 종료되었습니다. 로비로 돌아갑니다.`);
    window.location.reload();
});

playButton.addEventListener('click', () => {
    const selectedCards = document.querySelectorAll('#player-hand .card.selected');
    const hand_to_play = Array.from(selectedCards).map(card => ({ suit: card.dataset.suit, rank: parseInt(card.dataset.rank) }));
    if (hand_to_play.length > 0) { socket.emit('play_hand', hand_to_play); } 
    else { alert('카드를 선택해주세요!'); }
});

passButton.addEventListener('click', () => { socket.emit('pass_turn'); });

function redrawGame(gameState) {
    if (!gameState || !gameState.player_hands || myPlayerNum === -1) return;

    const myStatus = {
        isMyTurn: gameState.current_player_index === myPlayerNum,
        hasPassed: gameState.players_who_passed_this_round.includes(myPlayerNum),
        isLeader: gameState.last_played_hand_info[0] === null
    };

    playButton.disabled = !myStatus.isMyTurn || myStatus.hasPassed;
   // main.js 의 redrawGame 함수 내부
    passButton.disabled = !myStatus.isMyTurn || myStatus.isLeader;

    myHandDiv.innerHTML = '';
    const myHand = gameState.player_hands[myPlayerNum];
    myHand.forEach(tile => createCard(tile, myHandDiv, true));

    boardHandDiv.innerHTML = '';
    const lastPlayedTiles = gameState.last_played_tiles;
    if (lastPlayedTiles && lastPlayedTiles.length > 0) {
        lastPlayedTiles.forEach(tile => createCard(tile, boardHandDiv, false));
    }

    if (gameState.current_player_index === myPlayerNum) {
        gameInfoDiv.innerHTML = `<span class="turn-indicator">당신의 턴입니다!</span>`;
    } else {
        gameInfoDiv.innerHTML = `플레이어 ${gameState.current_player_index + 1}의 턴입니다.`;
    }

    statusTbody.innerHTML = '';
    const numPlayers = gameState.player_hands.length;
    for (let i = 0; i < numPlayers; i++) {
        const row = document.createElement('tr');
        let status = '';
        row.classList.remove('my-turn-indicator');
        if (i === gameState.current_player_index) {
            status = '진행 중';
            if (i === myPlayerNum) { row.classList.add('my-turn-indicator'); }
            else { row.classList.add('turn-row'); }
        } else if (gameState.players_who_passed_this_round.includes(i)) {
            status = 'Pass';
        }
        let playerName = `P${i + 1}`;
        if (i === myPlayerNum) {
            playerName += ' (당신)';
            row.classList.add('my-row');
        }
        const cardCount = gameState.player_hands[i].length;
        const money = gameState.player_money[i];
        row.innerHTML = `<td>${playerName}</td><td>${cardCount}개</td><td>${money}원</td><td>${status}</td>`;
        statusTbody.appendChild(row);
    }
    
    logList.innerHTML = '';
    if (gameState.game_log) {
        const lastMessage = gameState.game_log[gameState.game_log.length - 1];
        if (lastMessage && lastMessage.includes('냈습니다')) {
            playSound.currentTime = 0;
            playSound.play().catch(e => console.error("소리 재생 오류:", e));
        }
        gameState.game_log.forEach(message => {
            const li = document.createElement('li');
            li.textContent = message;
            logList.appendChild(li);
        });
        logList.scrollTop = logList.scrollHeight;
    }
}
        
function createCard(tile, container, isClickable) {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'card';
    cardDiv.dataset.suit = tile.suit;
    cardDiv.dataset.rank = tile.rank;
    cardDiv.style.backgroundImage = `url('/static/images/${tile.suit}_${tile.rank}.png')`;
    if (isClickable) {
        cardDiv.addEventListener('click', () => cardDiv.classList.toggle('selected'));
    }
    container.appendChild(cardDiv);
}
