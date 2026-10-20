import {$, afterCenterX, insideRect} from './dom.js';
import {t} from './i18n.js';

export function initFolders({confirmDelete, errText}) {
  const folderButtons = [...document.querySelectorAll('.fold[data-folder]')];
  const folderForm = $('#folder-form');
  const folderNameField = $('#folder-form [name=name]');
  const folderMsg = $('#fe-msg');
  const deleteFolderButton = $('#delete-folder');
  const folderSheet = $('#folder-sheet');
  const folderSheetClose = $('#folder-sheet .close');
  const folderEditButton = $('#folder-edit');
  const folderBackButton = $('#folder-back');
  const folderRow = $('.folders') || document.createElement('div');

  let curFolder = null;

  const folderEls = () => [...folderRow.querySelectorAll('.fold[data-folder]')];
  const getFolderNode = folderId => folderRow.querySelector(`.fold[data-folder="${folderId}"]`);

  const openFolderSheet = folder => {
    curFolder = folder;
    folderNameField.value = folder.name;
    folderMsg.textContent = '';
    folderSheet.hidden = false;
    folderNameField.focus();
  };

  const closeFolderSheet = () => {
    folderSheet.hidden = true;
  };

  const applyFolderName = name => {
    const tile = getFolderNode(curFolder.id);
    if (tile) {
      tile.dataset.name = name;
      const label = tile.querySelector('.fname');
      if (label) label.textContent = name;
    }
    // The edit button and the back label read the same folder, so keep them in
    // step without a full reload.
    folderEditButton.dataset.name = name;
    folderBackButton.textContent = '← ' + name;
    curFolder.name = name;
  };

  folderButtons.forEach(folder => {
    folder.onclick = () => {
      location.href = folder.classList.contains('on') ? '/' : '/?folder=' + folder.dataset.folder;
    };
  });

  if (folderEditButton) {
    folderBackButton.onclick = () => {
      location.href = '/';
    };
    folderEditButton.onclick = () => openFolderSheet({...folderEditButton.dataset});
  }

  folderSheetClose.onclick = closeFolderSheet;

  folderForm.onsubmit = async event => {
    event.preventDefault();
    let response;
    try {
      response = await fetch('/api/folders/' + curFolder.id, {
        method: 'PUT',
        body: new URLSearchParams(new FormData(folderForm)),
      });
    } catch {
      folderMsg.textContent = t('common.save_failed_connection');
      return;
    }

    if (!response.ok) {
      folderMsg.textContent = await errText(response);
      return;
    }

    applyFolderName(folderNameField.value.trim());
    closeFolderSheet();
  };

  deleteFolderButton.onclick = () => confirmDelete('folder', curFolder);

  const HOLD_MS = 400;
  let holdTimer = null;
  let holdPos = null;
  let holdPointer = null;
  let movingFolder = null;
  let dragPointer = null;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragMoved = false;
  let swallowFolder = false;
  let swallowTimer = null;

  const saveFolderOrder = async () => {
    const body = new URLSearchParams();
    folderEls().forEach(folder => body.append('ids', folder.dataset.folder));
    let response;
    try {
      response = await fetch('/api/folders/order', {method: 'POST', body});
    } catch {
      alert(t('folder.order_failed'));
      location.reload();
      return;
    }
    if (!response.ok) {
      alert(t('folder.order_failed'));
      location.reload();
    }
  };

  const exitFolderMove = () => {
    if (!movingFolder) return;
    movingFolder.classList.remove('moving-folder', 'dragging');
    movingFolder = null;
    dragPointer = null;
    dragMoved = false;
  };

  const enterFolderMove = folder => {
    if (movingFolder && movingFolder !== folder) exitFolderMove();
    movingFolder = folder;
    folder.classList.remove('holding');
    folder.classList.add('moving-folder');
    holdTimer = null;
    holdPos = null;
    holdPointer = null;
    clearTimeout(swallowTimer);
    swallowFolder = true;
  };

  const onFolderDragMove = event => {
    if (!movingFolder || event.pointerId !== dragPointer) return;
    if (Math.hypot(event.clientX - dragStartX, event.clientY - dragStartY) > 4) dragMoved = true;
    if (insideRect(movingFolder.getBoundingClientRect(), event.clientX, event.clientY)) return;

    const target = document.elementFromPoint(event.clientX, event.clientY)?.closest('.fold[data-folder]');
    const rect = target?.getBoundingClientRect();
    if (!target || target === movingFolder || !rect) return;

    const after = afterCenterX(rect, event.clientX);
    if (after === null) return;
    if (after) {
      if (movingFolder.previousElementSibling !== target) target.after(movingFolder);
    } else if (movingFolder.nextElementSibling !== target) {
      target.before(movingFolder);
    }
  };

  const endFolderDrag = event => {
    if (event && event.pointerId !== dragPointer) return;
    document.removeEventListener('pointermove', onFolderDragMove);
    document.removeEventListener('pointerup', endFolderDrag);
    document.removeEventListener('pointercancel', endFolderDrag);
    dragPointer = null;
    if (!movingFolder) return;
    movingFolder.classList.remove('dragging');
    const moved = dragMoved;
    swallowFolder = true;
    clearTimeout(swallowTimer);
    swallowTimer = setTimeout(() => { swallowFolder = false; }, 400);
    exitFolderMove();
    if (moved) saveFolderOrder();
  };

  const beginFolderDrag = (pointerId, x, y) => {
    if (!movingFolder || dragPointer !== null) return;
    dragPointer = pointerId;
    dragStartX = x;
    dragStartY = y;
    dragMoved = false;
    movingFolder.classList.add('dragging');
    document.addEventListener('pointermove', onFolderDragMove);
    document.addEventListener('pointerup', endFolderDrag);
    document.addEventListener('pointercancel', endFolderDrag);
  };

  const cancelFolderHold = folder => {
    clearTimeout(holdTimer);
    holdTimer = null;
    holdPos = null;
    holdPointer = null;
    folder.classList.remove('holding');
  };

  for (const folder of folderEls()) {
    folder.addEventListener('contextmenu', event => event.preventDefault());
    folder.addEventListener('keydown', event => {
      if (event.target === folder && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        folder.click();
      }
    });
    folder.addEventListener('pointerdown', event => {
      if (movingFolder || event.button > 0 || event.target.closest('button,input,select,summary,a')) return;
      holdPos = [event.clientX, event.clientY];
      holdPointer = event.pointerId;
      folder.classList.add('holding');
      holdTimer = setTimeout(() => {
        const pointer = holdPointer;
        const startX = holdPos ? holdPos[0] : event.clientX;
        const startY = holdPos ? holdPos[1] : event.clientY;
        enterFolderMove(folder);
        beginFolderDrag(pointer, startX, startY);
      }, HOLD_MS);
    });
    folder.addEventListener('pointermove', event => {
      if (holdPos && Math.hypot(event.clientX - holdPos[0], event.clientY - holdPos[1]) > 10) cancelFolderHold(folder);
    });
    for (const name of ['pointerup', 'pointercancel']) {
      folder.addEventListener(name, () => {
        if (holdTimer) cancelFolderHold(folder);
      });
    }
    folder.addEventListener('pointerleave', () => {
      if (!movingFolder && holdTimer) cancelFolderHold(folder);
    });
  }

  document.addEventListener('click', event => {
    if (swallowFolder) {
      swallowFolder = false;
      clearTimeout(swallowTimer);
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (!movingFolder) return;
    event.preventDefault();
    event.stopPropagation();
    exitFolderMove();
  }, true);

  addEventListener('keydown', event => {
    if (event.key === 'Escape') exitFolderMove();
  });
}
