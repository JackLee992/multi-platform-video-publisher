#!/usr/bin/env bash

set -euo pipefail

PORT="${CHROME_INJECT_PORT:-8765}"
HOST="${CHROME_INJECT_HOST:-127.0.0.1}"

usage() {
  cat <<'EOF'
Usage:
  chrome_current_session_publish.sh --video /abs/path.mov --title "Title" [options]

Options:
  --video PATH           Absolute path to local video file
  --cover PATH           Optional absolute path to local cover image
  --title TEXT           Shared title used across platforms
  --description TEXT     Optional description. Defaults to title
  --platform NAME        xiaohongshu | douyin | wechat_channels | all
  --port N               Local file server port. Default: 8765
  --skip-publish         Only upload and fill fields, do not click final publish

Examples:
  ./scripts/chrome_current_session_publish.sh \
    --video /Users/me/Downloads/test.mov \
    --title "第二次三端测试"

  ./scripts/chrome_current_session_publish.sh \
    --video /Users/me/Downloads/test.mov \
    --title "第二次三端测试" \
    --platform xiaohongshu
EOF
}

VIDEO_PATH=""
COVER_PATH=""
TITLE=""
DESCRIPTION=""
PLATFORM="all"
SKIP_PUBLISH="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --video)
      VIDEO_PATH="$2"
      shift 2
      ;;
    --cover)
      COVER_PATH="$2"
      shift 2
      ;;
    --title)
      TITLE="$2"
      shift 2
      ;;
    --description)
      DESCRIPTION="$2"
      shift 2
      ;;
    --platform)
      PLATFORM="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --skip-publish)
      SKIP_PUBLISH="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$VIDEO_PATH" || -z "$TITLE" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$VIDEO_PATH" ]]; then
  echo "Video not found: $VIDEO_PATH" >&2
  exit 1
fi

if [[ -z "$DESCRIPTION" ]]; then
  DESCRIPTION="$TITLE"
fi

if [[ -n "$COVER_PATH" && ! -f "$COVER_PATH" ]]; then
  echo "Cover not found: $COVER_PATH" >&2
  exit 1
fi

js_quote() {
  python3 -c 'import json, sys; print(json.dumps(sys.argv[1], ensure_ascii=False))' "$1"
}

JS_TITLE="$(js_quote "$TITLE")"
JS_DESCRIPTION="$(js_quote "$DESCRIPTION")"

escape_for_applescript() {
  python3 -c 'import sys; print(sys.argv[1].replace("\\\\", "\\\\\\\\").replace("\"", "\\\\\""))' "$1"
}

AS_JS_TITLE="$(escape_for_applescript "$JS_TITLE")"
AS_JS_DESCRIPTION="$(escape_for_applescript "$JS_DESCRIPTION")"

js_single_quoted_literal() {
  python3 -c "import sys; s=sys.argv[1]; print(\"'\" + s.replace('\\\\', '\\\\\\\\').replace(\"'\", \"\\\\'\").replace('\\n', '\\\\n') + \"'\")" "$1"
}

JS_TITLE_LITERAL="$(js_single_quoted_literal "$TITLE")"
JS_DESCRIPTION_LITERAL="$(js_single_quoted_literal "$DESCRIPTION")"

js_to_base64() {
  python3 -c 'import base64, sys; print(base64.b64encode(sys.argv[1].encode("utf-8")).decode("ascii"))' "$1"
}

VIDEO_DIR="$(cd "$(dirname "$VIDEO_PATH")" && pwd)"
VIDEO_FILE="$(basename "$VIDEO_PATH")"
COVER_FILE=""
COVER_BASE64=""
ASSET_DIR=""
ASSET_SERVER_SCRIPT="$(cd "$(dirname "$0")" && pwd)/chrome_current_session_asset_server.py"

ensure_server() {
  ASSET_DIR="$(mktemp -d /tmp/chrome-current-session-assets.XXXXXX)"
  ln -sf "$VIDEO_PATH" "$ASSET_DIR/$VIDEO_FILE"
  if [[ -n "$COVER_PATH" ]]; then
    COVER_FILE="$(basename "$COVER_PATH")"
    COVER_BASE64="$(python3 -c "import base64, pathlib, sys; print(base64.b64encode(pathlib.Path(sys.argv[1]).read_bytes()).decode('ascii'))" "$COVER_PATH")"
    ln -sf "$COVER_PATH" "$ASSET_DIR/$COVER_FILE"
  fi
  if ! lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    python3 "$ASSET_SERVER_SCRIPT" --host "$HOST" --port "$PORT" --directory "$ASSET_DIR" >/tmp/chrome-current-session-publish.log 2>&1 &
    SERVER_PID=$!
    sleep 1
  else
    SERVER_PID=""
  fi
}

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${ASSET_DIR:-}" && -d "${ASSET_DIR:-}" ]]; then
    rm -rf "$ASSET_DIR"
  fi
}

trap cleanup EXIT

ensure_server

curl -fsSI "http://${HOST}:${PORT}/${VIDEO_FILE}" >/dev/null

run_osascript() {
  osascript - "$@"
}

platform_editor_url() {
  local platform_name="$1"

  case "$platform_name" in
    xiaohongshu)
      echo "https://creator.xiaohongshu.com/publish/publish"
      ;;
    douyin)
      echo "https://creator.douyin.com/creator-micro/content/upload"
      ;;
    wechat_channels)
      echo "https://channels.weixin.qq.com/platform/post/create"
      ;;
    *)
      return 1
      ;;
  esac
}

wait_for_platform_tab() {
  local platform_name="$1"
  local match_expr=""

  case "$platform_name" in
    xiaohongshu)
      match_expr='tabUrl starts with "https://creator.xiaohongshu.com/publish/publish"'
      ;;
    douyin)
      match_expr='tabUrl starts with "https://creator.douyin.com/creator-micro/content/upload" or tabUrl starts with "https://creator.douyin.com/creator-micro/content/post/video"'
      ;;
    wechat_channels)
      match_expr='tabUrl starts with "https://channels.weixin.qq.com/platform/post/create"'
      ;;
    *)
      return 1
      ;;
  esac

  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 20 times
    repeat with w in windows
      repeat with i from 1 to (count of tabs of w)
        set t to tab i of w
        set tabUrl to (URL of t as text)
        if ${match_expr} then
          return "ready"
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "timeout"
APPLESCRIPT
}

ensure_platform_tab() {
  local platform_name="$1"
  local editor_url
  editor_url="$(platform_editor_url "$platform_name")"

  if [[ "$(wait_for_platform_tab "$platform_name")" == "ready" ]]; then
    return 0
  fi

  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  activate
  if (count of windows) is 0 then
    make new window
  end if
  tell front window
    make new tab with properties {URL:"${editor_url}"}
    set active tab index to (count of tabs)
  end tell
end tell
APPLESCRIPT

  if [[ "$(wait_for_platform_tab "$platform_name")" != "ready" ]]; then
    echo "Timed out waiting for ${platform_name} editor tab" >&2
    exit 1
  fi
}

wait_for_fill_target() {
  local platform_name="$1"
  local js_probe=""
  local url_match=""

  case "$platform_name" in
    xiaohongshu)
      url_match='tabUrl starts with "https://creator.xiaohongshu.com/publish/publish"'
      js_probe="(() => !!Array.from(document.querySelectorAll('input')).find(el => (el.placeholder || '').includes('填写标题')))()"
      ;;
    douyin)
      url_match='tabUrl starts with "https://creator.douyin.com/creator-micro/content/upload" or tabUrl starts with "https://creator.douyin.com/creator-micro/content/post/video"'
      js_probe="(() => !!Array.from(document.querySelectorAll('input')).find(el => (el.placeholder || '').includes('填写作品标题')))()"
      ;;
    wechat_channels)
      url_match='tabUrl starts with "https://channels.weixin.qq.com/platform/post/create"'
      js_probe="(() => { const root = document.querySelector('wujie-app')?.shadowRoot || document; return !!Array.from(root.querySelectorAll('input')).find(el => { const placeholder = el.placeholder || ''; return placeholder.includes('6-16个字符') || placeholder.includes('概括视频主要内容') || placeholder.includes('概括视频主要内容，字数建议6-16个字符'); }); })()"
      ;;
    *)
      return 1
      ;;
  esac

  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 60 times
    repeat with w in windows
      repeat with i from 1 to (count of tabs of w)
        set t to tab i of w
        set tabUrl to (URL of t as text)
        if ${url_match} then
          set readyState to execute t javascript "${js_probe}"
          if readyState is "true" then return "ready"
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "timeout"
APPLESCRIPT
}

wait_for_upload_input() {
  local platform_name="$1"
  local js_probe=""
  local url_match=""

  case "$platform_name" in
    xiaohongshu)
      url_match='tabUrl starts with "https://creator.xiaohongshu.com/publish/publish"'
      js_probe="(() => !!document.querySelector('input[type=file]'))()"
      ;;
    douyin)
      url_match='tabUrl starts with "https://creator.douyin.com/creator-micro/content/upload" or tabUrl starts with "https://creator.douyin.com/creator-micro/content/post/video"'
      js_probe="(() => !!document.querySelector('input[type=file]'))()"
      ;;
    wechat_channels)
      url_match='tabUrl starts with "https://channels.weixin.qq.com/platform/post/create"'
      js_probe="(() => { const root = document.querySelector('wujie-app')?.shadowRoot || document; return !!root.querySelector('input[type=file]'); })()"
      ;;
    *)
      return 1
      ;;
  esac

  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 30 times
    repeat with w in windows
      repeat with i from 1 to (count of tabs of w)
        set t to tab i of w
        set tabUrl to (URL of t as text)
        if ${url_match} then
          set readyState to execute t javascript "${js_probe}"
          if readyState is "true" then return "ready"
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "timeout"
APPLESCRIPT
}

handle_douyin_resume_prompt() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      set tabUrl to (URL of t as text)
      if tabUrl starts with "https://creator.douyin.com/creator-micro/content/upload" or tabUrl starts with "https://creator.douyin.com/creator-micro/content/post/video" then
        set js to "(() => { const bodyText = (document.body && document.body.innerText) || ''; if (!bodyText.includes('你还有上次未发布的视频，是否继续编辑？')) return JSON.stringify({ok:true,action:'no_prompt'}); const abandon = Array.from(document.querySelectorAll('button,div,span')).find(el => (el.innerText || '').trim() === '放弃'); if (!abandon) return JSON.stringify({ok:false,error:'missing abandon button'}); abandon.click(); return JSON.stringify({ok:true,action:'discard_previous_draft'}); })()"
        return execute t javascript js
      end if
    end repeat
  end repeat
end tell
return "{\"ok\":true,\"action\":\"not_found\"}"
APPLESCRIPT
}

handle_wechat_channels_dialogs() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 5 times
    repeat with w in windows
      repeat with t in tabs of w
        set tabUrl to (URL of t as text)
        if tabUrl starts with "https://channels.weixin.qq.com/platform/post/create" then
          set js to "(() => { const root = document.querySelector('wujie-app')?.shadowRoot || document; const bodyText = (root.innerText || document.body?.innerText || ''); const clickByText = (text) => { const target = Array.from(root.querySelectorAll('button,div,span')).find(el => (el.innerText || '').trim() === text); if (!target) return false; target.click(); return true; }; if (bodyText.includes('将此次编辑保留?')) { if (clickByText('不保存')) return JSON.stringify({ok:true,action:'discard_modal'}); } if (bodyText.includes('我知道了')) { if (clickByText('我知道了')) return JSON.stringify({ok:true,action:'acknowledged'}); } if (bodyText.includes('你还不能发表视频') || bodyText.includes('管理员本人验证')) { return JSON.stringify({ok:false,error:'wechat_channels_permission_blocked'}); } return JSON.stringify({ok:true,action:'clear'}); })()"
          set resultJson to execute t javascript js
          if resultJson is not "{\"ok\":true,\"action\":\"clear\"}" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "{\"ok\":true,\"action\":\"clear\"}"
APPLESCRIPT
}

focus_platform_tab() {
  local platform_name="$1"
  local match_expr=""

  case "$platform_name" in
    xiaohongshu)
      match_expr='url starts with "https://creator.xiaohongshu.com/publish/publish" or url starts with "https://creator.xiaohongshu.com/publish/success"'
      ;;
    douyin)
      match_expr='url starts with "https://creator.douyin.com/creator-micro/content/upload" or url starts with "https://creator.douyin.com/creator-micro/content/post/video" or url starts with "https://creator.douyin.com/creator-micro/content/manage"'
      ;;
    wechat_channels)
      match_expr='url starts with "https://channels.weixin.qq.com/platform/post/create" or url starts with "https://channels.weixin.qq.com/platform/post/list"'
      ;;
    *)
      return 0
      ;;
  esac

  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  activate
  set matchedWindow to missing value
  set matchedTabIndex to 0
  repeat with w in windows
    repeat with i from 1 to (count of tabs of w)
      set t to tab i of w
      set tabUrl to (URL of t as text)
      if ${match_expr//url/tabUrl} then
        set matchedWindow to w
        set matchedTabIndex to i
      end if
    end repeat
  end repeat
  if matchedWindow is not missing value then
    set active tab index of matchedWindow to matchedTabIndex
    set index of matchedWindow to 1
    return "focused"
  end if
end tell
return "not_found"
APPLESCRIPT
}

upload_via_native_file_picker() {
  local platform_name="$1"
  local opener_js=""
  local url_match=""

  case "$platform_name" in
    xiaohongshu)
      url_match='tabUrl starts with "https://creator.xiaohongshu.com/publish/publish"'
      opener_js="(() => { const input = document.querySelector('input[type=file]'); if (!input) return 'missing_input'; if (input.showPicker) { input.showPicker(); return 'picker_opened'; } input.click(); return 'clicked'; })()"
      ;;
    douyin)
      url_match='tabUrl starts with "https://creator.douyin.com/creator-micro/content/upload" or tabUrl starts with "https://creator.douyin.com/creator-micro/content/post/video"'
      opener_js="(() => { const input = Array.from(document.querySelectorAll('input[type=file]')).find(el => (el.accept || '').includes('video/')); if (!input) return 'missing_input'; if (input.showPicker) { input.showPicker(); return 'picker_opened'; } input.click(); return 'clicked'; })()"
      ;;
    wechat_channels)
      url_match='tabUrl starts with "https://channels.weixin.qq.com/platform/post/create"'
      opener_js="(() => { const root = document.querySelector('wujie-app')?.shadowRoot || document; const input = root.querySelector('input[type=file]'); if (!input) return 'missing_input'; if (input.showPicker) { input.showPicker(); return 'picker_opened'; } input.click(); return 'clicked'; })()"
      ;;
    *)
      return 1
      ;;
  esac

  focus_platform_tab "$platform_name" >/dev/null
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  activate
  repeat with w in windows
    repeat with t in tabs of w
      set tabUrl to (URL of t as text)
      if ${url_match} then
        execute t javascript "${opener_js}"
        exit repeat
      end if
    end repeat
  end repeat
end tell

delay 0.6
tell application "System Events"
  keystroke "g" using {command down, shift down}
  delay 0.3
  keystroke "${VIDEO_PATH}"
  delay 0.3
  key code 36
  delay 0.5
  key code 36
end tell
APPLESCRIPT

  echo "{\"ok\":true,\"action\":\"native_picker_submitted\",\"platform\":\"${platform_name}\"}"
}

json_failed() {
  local result_json="$1"
  [[ "$result_json" == *"\"ok\":false"* ]] || [[ "$result_json" == "timeout" ]]
}

upload_xiaohongshu() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 20 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
          set js to "window.__codexUploadResult='starting'; (async () => { try { const input = document.querySelector('input[type=file]'); if (!input) throw new Error('missing input'); const fetchAssetBlob = async (name) => { const urls = ['http://${HOST}:${PORT}/' + name, 'http://localhost:${PORT}/' + name]; let lastError = null; for (const url of urls) { for (let attempt = 1; attempt <= 3; attempt += 1) { try { const res = await fetch(url, { cache: 'no-store' }); if (!res.ok) throw new Error('bad status ' + res.status + ' for ' + url); return await res.blob(); } catch (error) { lastError = error; await new Promise(resolve => setTimeout(resolve, attempt * 400)); } } } throw lastError || new Error('failed to fetch asset'); }; const blob = await fetchAssetBlob('${VIDEO_FILE}'); const file = new File([blob], '${VIDEO_FILE}', {type: blob.type || 'video/quicktime'}); const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); window.__codexUploadResult = JSON.stringify({ok:true, files: input.files.length, name: input.files[0] && input.files[0].name, size: input.files[0] && input.files[0].size}); } catch (error) { window.__codexUploadResult = JSON.stringify({ok:false, error: String(error)}); } })(); document.querySelector('input[type=file]') ? 'scheduled' : 'retry'"
          set uploadState to execute t javascript js
          if uploadState is "scheduled" then return uploadState
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "timeout"
APPLESCRIPT
}

poll_xiaohongshu_upload() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
          set resultJson to execute t javascript "window.__codexUploadResult || ''"
          if resultJson is not "" and resultJson is not "starting" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "timeout"
end tell
APPLESCRIPT
}

fill_xiaohongshu() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 90 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
          set js to "(() => { const title = ${JS_TITLE_LITERAL}; const titleInput = Array.from(document.querySelectorAll('input')).find(el => (el.placeholder || '').includes('填写标题')); if (!titleInput) return JSON.stringify({ok:false,error:'missing title input'}); const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; setter.call(titleInput, title); titleInput.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: title })); titleInput.dispatchEvent(new Event('change', { bubbles: true })); titleInput.dispatchEvent(new Event('blur', { bubbles: true })); return JSON.stringify({ok:true, title:titleInput.value}); })()"
          set resultJson to execute t javascript js
          if resultJson contains "\"ok\":true" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "{\"ok\":false,\"error\":\"missing title input\"}"
APPLESCRIPT
}

fill_xiaohongshu_description() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 45 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
          set js to "(() => { const desc = ${JS_DESCRIPTION_LITERAL}; const editor = document.querySelector('[contenteditable=true]'); if (!editor) return JSON.stringify({ok:false,error:'missing description editor'}); editor.focus(); editor.innerHTML = ''; editor.textContent = desc; editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: desc })); editor.dispatchEvent(new Event('change', { bubbles: true })); editor.dispatchEvent(new Event('blur', { bubbles: true })); return JSON.stringify({ok:true, description:editor.innerText}); })()"
          set resultJson to execute t javascript js
          if resultJson contains "\"ok\":true" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "{\"ok\":false,\"error\":\"missing description editor\"}"
APPLESCRIPT
}

apply_xiaohongshu_cover() {
  if [[ -n "$COVER_FILE" ]]; then
    run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 45 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
          set js to "window.__codexXhsCover='starting'; (async () => { try { const clickByText = (texts) => { for (const text of texts) { const target = Array.from(document.querySelectorAll('button,div,span')).find(el => (el.innerText || '').trim() === text); if (target) { target.click(); return text; } } return null; }; const bytesFromBase64 = (value) => Uint8Array.from(atob(value), c => c.charCodeAt(0)); clickByText(['设置封面', '修改封面']); await new Promise(resolve => setTimeout(resolve, 800)); const input = Array.from(document.querySelectorAll('input[type=file]')).find(el => ((el.accept || '').includes('image/png, image/jpeg, image/*') || (el.accept || '').includes('image/'))); if (!input) throw new Error('missing xiaohongshu cover input'); const bytes = bytesFromBase64('${COVER_BASE64}'); const file = new File([bytes], '${COVER_FILE}', {type: 'image/jpeg'}); const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); await new Promise(resolve => setTimeout(resolve, 1200)); const confirm = Array.from(document.querySelectorAll('button,div,span')).find(el => ['确定', '完成', '确认'].includes((el.innerText || '').trim())); if (confirm) confirm.click(); await new Promise(resolve => setTimeout(resolve, 1200)); const preview = Array.from(document.querySelectorAll('[style*=\"background-image\"], img')).find(el => { const style = el.getAttribute && el.getAttribute('style'); const src = el.getAttribute && el.getAttribute('src'); return (style && style.includes('blob:')) || (src && src.startsWith('blob:')); }); window.__codexXhsCover = JSON.stringify({ok:true, action:'custom_cover_uploaded', files: input.files.length, preview: !!preview}); } catch (error) { window.__codexXhsCover = JSON.stringify({ok:false, error: String(error)}); } })(); 'scheduled'"
          return execute t javascript js
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "timeout"
APPLESCRIPT
    run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
          set resultJson to execute t javascript "window.__codexXhsCover || ''"
          if resultJson is not "" and resultJson is not "starting" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "timeout"
end tell
APPLESCRIPT
    return 0
  fi

  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
        set js to "(() => { const prefer = Array.from(document.querySelectorAll('button,div,span')).find(el => (el.innerText || '').trim() === '智能推荐封面'); if (prefer) { prefer.click(); return JSON.stringify({ok:true, action:'smart_cover_clicked'}); } const header = Array.from(document.querySelectorAll('button,div,span')).find(el => (el.innerText || '').trim() === '设置封面' || (el.innerText || '').trim() === '修改封面'); if (header) { header.click(); return JSON.stringify({ok:true, action:'cover_panel_opened'}); } return JSON.stringify({ok:true, action:'default_cover_retained'}); })()"
        return execute t javascript js
      end if
    end repeat
  end repeat
end tell
return "{\"ok\":true,\"action\":\"not_found\"}"
APPLESCRIPT
}

publish_xiaohongshu() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
          set marker to execute t javascript "(() => { const btn = Array.from(document.querySelectorAll('button')).find(el => (el.innerText || '').trim() === '发布' && !el.disabled); return btn ? 'MATCH' : ''; })()"
          if marker is "MATCH" then
            return execute t javascript "(() => { const btn = Array.from(document.querySelectorAll('button')).find(el => (el.innerText || '').trim() === '发布' && !el.disabled); if (!btn) return JSON.stringify({ok:false,error:'missing publish'}); btn.click(); return JSON.stringify({ok:true,text:btn.innerText,url:location.href}); })()"
          end if
        end if
    end repeat
    end repeat
    delay 1
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

check_xiaohongshu_result() {
  sleep 4
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) contains "creator.xiaohongshu.com" then
        set bodyText to execute t javascript "(document.body && document.body.innerText || '').slice(0,1200)"
        if (URL of t as text) contains "/publish/success" or bodyText contains "发布成功" then
          return (URL of t as text) & linefeed & bodyText
        end if
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

upload_douyin() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 20 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
          set js to "window.__codexDouyinUpload='starting'; (async () => { try { const input = document.querySelector('input[type=file]'); if (!input) throw new Error('missing input'); const fetchAssetBlob = async (name) => { const urls = ['http://${HOST}:${PORT}/' + name, 'http://localhost:${PORT}/' + name]; let lastError = null; for (const url of urls) { for (let attempt = 1; attempt <= 3; attempt += 1) { try { const res = await fetch(url, { cache: 'no-store' }); if (!res.ok) throw new Error('bad status ' + res.status + ' for ' + url); return await res.blob(); } catch (error) { lastError = error; await new Promise(resolve => setTimeout(resolve, attempt * 400)); } } } throw lastError || new Error('failed to fetch asset'); }; const blob = await fetchAssetBlob('${VIDEO_FILE}'); const file = new File([blob], '${VIDEO_FILE}', {type: blob.type || 'video/quicktime'}); const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); window.__codexDouyinUpload = JSON.stringify({ok:true, files: input.files.length, name: input.files[0] && input.files[0].name, size: input.files[0] && input.files[0].size}); } catch (error) { window.__codexDouyinUpload = JSON.stringify({ok:false, error: String(error)}); } })(); document.querySelector('input[type=file]') ? 'scheduled' : 'retry'"
          set uploadState to execute t javascript js
          if uploadState is "scheduled" then return uploadState
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "timeout"
APPLESCRIPT
}

poll_douyin_upload() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
          set resultJson to execute t javascript "window.__codexDouyinUpload || ''"
          if resultJson is not "" and resultJson is not "starting" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "timeout"
end tell
APPLESCRIPT
}

fill_douyin() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 90 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
          set js to "(() => { const title = ${JS_TITLE_LITERAL}; const desc = ${JS_DESCRIPTION_LITERAL}; const titleInput = Array.from(document.querySelectorAll('input')).find(el => (el.placeholder || '').includes('填写作品标题')); if (!titleInput) return JSON.stringify({ok:false,error:'missing title input'}); const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; setter.call(titleInput, title); titleInput.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: title })); titleInput.dispatchEvent(new Event('change', { bubbles: true })); titleInput.dispatchEvent(new Event('blur', { bubbles: true })); const editor = document.querySelector('[contenteditable=true]'); if (editor) { editor.focus(); editor.innerHTML = ''; editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward', data: null })); editor.textContent = desc; editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: desc })); editor.dispatchEvent(new Event('change', { bubbles: true })); editor.dispatchEvent(new Event('blur', { bubbles: true })); } return JSON.stringify({ok:true, title:titleInput.value, editorText: editor ? editor.innerText : null}); })()"
          set resultJson to execute t javascript js
          if resultJson contains "\"ok\":true" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "{\"ok\":false,\"error\":\"missing title input\"}"
APPLESCRIPT
}

apply_douyin_cover() {
  if [[ -z "$COVER_FILE" ]]; then
    echo "{\"ok\":true,\"action\":\"no_cover_path\"}"
    return 0
  fi

  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 45 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
          set js to "window.__codexDouyinCover='starting'; (async () => { try { const bytesFromBase64 = (value) => Uint8Array.from(atob(value), c => c.charCodeAt(0)); const clickByExactText = (text) => { const target = Array.from(document.querySelectorAll('button,div,span')).find(el => (el.innerText || '').trim() === text); if (!target) return false; target.click(); return true; }; const clickNthChooseCover = (index) => { const targets = Array.from(document.querySelectorAll('button,div,span')).filter(el => (el.innerText || '').trim() === '选择封面'); const target = targets[index]; if (!target) return false; target.click(); return true; }; const uploadInput = () => Array.from(document.querySelectorAll('input[type=file]')).find(el => ((el.parentElement && (el.parentElement.className || '').includes('semi-upload upload-BvM5FF')) || (el.className || '').includes('semi-upload-hidden-input')) && (el.accept || '').includes('image/png')) || document.querySelector('.semi-upload.upload-BvM5FF input[type=file]'); const assignCover = () => { const input = uploadInput(); if (!input) throw new Error('missing douyin cover input'); const bytes = bytesFromBase64('${COVER_BASE64}'); const file = new File([bytes], '${COVER_FILE}', {type: 'image/jpeg'}); const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); return input.files.length; }; if (!clickNthChooseCover(0)) throw new Error('missing douyin choose cover'); await new Promise(resolve => setTimeout(resolve, 800)); const firstFiles = assignCover(); await new Promise(resolve => setTimeout(resolve, 1200)); clickByExactText('保存'); await new Promise(resolve => setTimeout(resolve, 1200)); clickByExactText('设置横封面'); await new Promise(resolve => setTimeout(resolve, 800)); const secondFiles = assignCover(); await new Promise(resolve => setTimeout(resolve, 1200)); clickByExactText('保存'); await new Promise(resolve => setTimeout(resolve, 1200)); clickByExactText('完成'); await new Promise(resolve => setTimeout(resolve, 1200)); window.__codexDouyinCover = JSON.stringify({ok:true, action:'douyin_cover_uploaded', files:firstFiles + secondFiles}); } catch (error) { window.__codexDouyinCover = JSON.stringify({ok:false, error: String(error)}); } })(); 'scheduled'"
          return execute t javascript js
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "timeout"
APPLESCRIPT
}

poll_douyin_cover() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
          set resultJson to execute t javascript "window.__codexDouyinCover || ''"
          if resultJson is not "" and resultJson is not "starting" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "timeout"
end tell
APPLESCRIPT
}

verify_douyin_cover() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 30 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
          set js to "(() => { const bodyText = (document.body && document.body.innerText) || ''; const warningMissing = !bodyText.includes('横/竖双封面缺失'); const modalClosed = !Array.from(document.querySelectorAll('button,div,span')).some(el => (el.innerText || '').trim() === '设置横封面'); const previewBlobCount = Array.from(document.querySelectorAll('img')).filter(img => ((img.getAttribute('src') || img.src || '').startsWith('blob:'))).length; if (warningMissing) return JSON.stringify({ok:true, action:'douyin_cover_verified', previewBlobCount, modalClosed}); return JSON.stringify({ok:false, error:'douyin_cover_not_verified', previewBlobCount, modalClosed}); })()"
          set resultJson to execute t javascript js
          if resultJson contains "\"action\":\"douyin_cover_verified\"" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "{\"ok\":false,\"error\":\"douyin_cover_not_verified\"}"
end tell
APPLESCRIPT
}

dismiss_douyin_cover_prompt() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 15 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
          set js to "(() => { const bodyText = (document.body && document.body.innerText) || ''; const clickByExactText = (text) => { const target = Array.from(document.querySelectorAll('button,div,span')).find(el => (el.innerText || '').trim() === text); if (!target) return false; target.click(); return true; }; if (!bodyText.includes('设置横封面获更多流量')) return JSON.stringify({ok:true, action:'no_prompt'}); if (clickByExactText('暂不设置')) return JSON.stringify({ok:true, action:'dismissed_horizontal_cover_prompt'}); if (clickByExactText('完成')) return JSON.stringify({ok:true, action:'clicked_finish'}); return JSON.stringify({ok:false, error:'douyin_horizontal_cover_prompt_still_open'}); })()"
          set resultJson to execute t javascript js
          if resultJson contains "\"ok\":true" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "{\"ok\":false,\"error\":\"douyin_horizontal_cover_prompt_still_open\"}"
end tell
APPLESCRIPT
}

publish_douyin() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
        return execute t javascript "(() => { const btn = Array.from(document.querySelectorAll('button')).find(el => (el.innerText || '').includes('发布') && !(el.innerText || '').includes('高清发布')); if (!btn) return JSON.stringify({ok:false,error:'missing publish'}); btn.click(); return JSON.stringify({ok:true,text:btn.innerText,url:location.href}); })()"
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

check_douyin_result() {
  sleep 5
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) contains "creator.douyin.com" then
        set bodyText to execute t javascript "(document.body && document.body.innerText || '').slice(0,1200)"
        if (URL of t as text) contains "/content/manage" then
          return (URL of t as text) & linefeed & bodyText
        end if
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

upload_wechat_channels() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 20 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
          set js to "window.__codexWxUpload='starting'; (async () => { try { const root = document.querySelector('wujie-app')?.shadowRoot || document; const input = root.querySelector('input[type=file]'); if (!input) throw new Error('missing shadow input'); const fetchAssetBlob = async (name) => { const urls = ['http://${HOST}:${PORT}/' + name, 'http://localhost:${PORT}/' + name]; let lastError = null; for (const url of urls) { for (let attempt = 1; attempt <= 3; attempt += 1) { try { const res = await fetch(url, { cache: 'no-store' }); if (!res.ok) throw new Error('bad status ' + res.status + ' for ' + url); return await res.blob(); } catch (error) { lastError = error; await new Promise(resolve => setTimeout(resolve, attempt * 400)); } } } throw lastError || new Error('failed to fetch asset'); }; const blob = await fetchAssetBlob('${VIDEO_FILE}'); const file = new File([blob], '${VIDEO_FILE}', {type: blob.type || 'video/quicktime'}); const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); window.__codexWxUpload = JSON.stringify({ok:true, files: input.files.length, name: input.files[0] && input.files[0].name, size: input.files[0] && input.files[0].size}); } catch (error) { window.__codexWxUpload = JSON.stringify({ok:false, error: String(error)}); } })(); (document.querySelector('wujie-app')?.shadowRoot || document).querySelector('input[type=file]') ? 'scheduled' : 'retry'"
          set uploadState to execute t javascript js
          if uploadState is "scheduled" then return uploadState
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "timeout"
APPLESCRIPT
}

poll_wechat_channels_upload() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
          set resultJson to execute t javascript "window.__codexWxUpload || ''"
          if resultJson is not "" and resultJson is not "starting" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "timeout"
end tell
APPLESCRIPT
}

fill_wechat_channels() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 90 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
          set js to "(() => { const root = document.querySelector('wujie-app')?.shadowRoot || document; const title = ${JS_TITLE_LITERAL}; const titleInput = Array.from(root.querySelectorAll('input')).find(el => { const placeholder = el.placeholder || ''; return placeholder.includes('6-16个字符') || placeholder.includes('概括视频主要内容') || placeholder.includes('概括视频主要内容，字数建议6-16个字符'); }); if (!titleInput) return JSON.stringify({ok:false,error:'missing short title input'}); const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; setter.call(titleInput, title); titleInput.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: title })); titleInput.dispatchEvent(new Event('change', { bubbles: true })); titleInput.dispatchEvent(new Event('blur', { bubbles: true })); return JSON.stringify({ok:true, title:titleInput.value, placeholder:titleInput.placeholder}); })()"
          set resultJson to execute t javascript js
          if resultJson contains "\"ok\":true" then return resultJson
        end if
        end repeat
    end repeat
    delay 1
  end repeat
end tell
return "{\"ok\":false,\"error\":\"missing short title input\"}"
APPLESCRIPT
}

fill_wechat_channels_description() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 45 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
          set js to "(() => { const root = document.querySelector('wujie-app')?.shadowRoot || document; const desc = ${JS_DESCRIPTION_LITERAL}; const editor = root.querySelector('.post-desc-box .input-editor'); if (!editor) return JSON.stringify({ok:false,error:'missing description editor'}); editor.focus(); editor.innerHTML = ''; editor.textContent = desc; editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: desc })); editor.dispatchEvent(new Event('change', { bubbles: true })); editor.dispatchEvent(new Event('blur', { bubbles: true })); return JSON.stringify({ok:true, description:editor.innerText}); })()"
          set resultJson to execute t javascript js
          if resultJson contains "\"ok\":true" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
end tell
return "{\"ok\":false,\"error\":\"missing description editor\"}"
APPLESCRIPT
}

apply_wechat_channels_cover() {
  if [[ -z "$COVER_FILE" ]]; then
    echo "{\"ok\":true,\"action\":\"no_cover_path\"}"
    return 0
  fi

  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat 45 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
          set js to "window.__codexWxCover='starting'; (async () => { try { const root = document.querySelector('wujie-app')?.shadowRoot || document; const clickByText = (text) => { const target = Array.from(root.querySelectorAll('button,div,span')).find(el => (el.innerText || '').trim() === text); if (!target) return false; target.click(); return true; }; const bytesFromBase64 = (value) => Uint8Array.from(atob(value), c => c.charCodeAt(0)); clickByText('编辑'); clickByText('上传封面'); const inputs = Array.from(root.querySelectorAll('input[type=file]')); const input = inputs[inputs.length - 1]; if (!input) throw new Error('missing cover input'); const bytes = bytesFromBase64('${COVER_BASE64}'); const file = new File([bytes], '${COVER_FILE}', {type: 'image/jpeg'}); const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); setTimeout(() => { clickByText('确定'); clickByText('确认'); }, 1200); window.__codexWxCover = JSON.stringify({ok:true, action:'cover_uploaded', files: input.files.length}); } catch (error) { window.__codexWxCover = JSON.stringify({ok:false, error: String(error)}); } })(); 'scheduled'"
          return execute t javascript js
        end if
      end repeat
    end repeat
  end repeat
end tell
return "NOT_FOUND"
APPLESCRIPT
}

poll_wechat_channels_cover() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
          set resultJson to execute t javascript "window.__codexWxCover || ''"
          if resultJson is not "" and resultJson is not "starting" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "timeout"
end tell
APPLESCRIPT
}

verify_wechat_channels_cover() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
          set js to "(() => { const root = document.querySelector('wujie-app')?.shadowRoot || document; const preview = root.querySelector('.cover-preview-wrap .vertical-img-size.cover-img-vertical'); const src = preview ? (preview.getAttribute('src') || preview.src || '') : ''; const dialog = root.querySelector('.cover-preview-wrap .weui-desktop-dialog__wrp'); const dialogHidden = !dialog || getComputedStyle(dialog).display === 'none'; if (src && dialogHidden) return JSON.stringify({ok:true, action:'cover_verified', src}); return JSON.stringify({ok:false, error:'cover_not_verified', src, dialogHidden}); })()"
          set resultJson to execute t javascript js
          if resultJson contains "\"action\":\"cover_verified\"" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "{\"ok\":false,\"error\":\"cover_not_verified\"}"
end tell
APPLESCRIPT
}

wait_for_wechat_channels_publish_ready() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 45 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
          set js to "(() => { const root = document.querySelector('wujie-app')?.shadowRoot || document; const bodyText = ((root && root.innerText) || document.body?.innerText || ''); const publishButton = Array.from(root.querySelectorAll('button')).find(el => (el.innerText || '').trim() === '发表'); const blockedByProgress = bodyText.includes('上传中') || bodyText.includes('处理中') || bodyText.includes('生成中'); if (!publishButton) return JSON.stringify({ok:false, error:'missing publish'}); if (publishButton.disabled) return JSON.stringify({ok:false, error:'publish_disabled'}); if (blockedByProgress) return JSON.stringify({ok:false, error:'publish_blocked_by_progress'}); return JSON.stringify({ok:true, action:'publish_ready'}); })()"
          set resultJson to execute t javascript js
          if resultJson contains "\"action\":\"publish_ready\"" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "{\"ok\":false,\"error\":\"publish_not_ready\"}"
end tell
APPLESCRIPT
}

publish_wechat_channels() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
        return execute t javascript "(() => { const shadow = document.querySelector('wujie-app')?.shadowRoot; const btn = shadow && Array.from(shadow.querySelectorAll('button')).find(el => (el.innerText || '').trim() === '发表'); if (!btn) return JSON.stringify({ok:false,error:'missing publish'}); btn.click(); return JSON.stringify({ok:true,text:btn.innerText,url:location.href}); })()"
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

check_wechat_channels_result() {
  sleep 5
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/" then
        set js to "(() => { const shadow = document.querySelector('wujie-app')?.shadowRoot; const text = shadow ? (shadow.innerText || '').slice(0,1200) : ((document.body && document.body.innerText) || '').slice(0,1200); return JSON.stringify({url: location.href, text}); })()"
        return execute t javascript js
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

run_platform() {
  local platform_name="$1"
  echo "==> ${platform_name}"
  ensure_platform_tab "$platform_name"
  focus_platform_tab "$platform_name" >/dev/null

  case "$platform_name" in
    xiaohongshu)
      echo "[${platform_name}] upload_start"
      upload_xiaohongshu
      xiaohongshu_upload_result="$(poll_xiaohongshu_upload)"
      echo "$xiaohongshu_upload_result"
      if json_failed "$xiaohongshu_upload_result"; then
        echo "[${platform_name}] upload_fallback_native_picker"
        upload_via_native_file_picker "$platform_name"
      fi
      focus_platform_tab "$platform_name" >/dev/null
      echo "[${platform_name}] fill_start"
      fill_xiaohongshu
      echo "[${platform_name}] description_start"
      fill_xiaohongshu_description
      echo "[${platform_name}] cover_start"
      apply_xiaohongshu_cover
      if [[ "$SKIP_PUBLISH" == "false" ]]; then
        echo "[${platform_name}] publish_start"
        publish_xiaohongshu
        check_xiaohongshu_result
      fi
      ;;
    douyin)
      echo "[${platform_name}] discard_old_draft_check"
      handle_douyin_resume_prompt
      focus_platform_tab "$platform_name" >/dev/null
      echo "[${platform_name}] upload_start"
      upload_douyin
      douyin_upload_result="$(poll_douyin_upload)"
      echo "$douyin_upload_result"
      if json_failed "$douyin_upload_result"; then
        echo "[${platform_name}] upload_fallback_native_picker"
        upload_via_native_file_picker "$platform_name"
      fi
      echo "[${platform_name}] discard_old_draft_check"
      handle_douyin_resume_prompt
      focus_platform_tab "$platform_name" >/dev/null
      echo "[${platform_name}] fill_start"
      fill_douyin
      echo "[${platform_name}] cover_start"
      apply_douyin_cover
      poll_douyin_cover
      verify_douyin_cover
      dismiss_douyin_cover_prompt
      if [[ "$SKIP_PUBLISH" == "false" ]]; then
        echo "[${platform_name}] publish_start"
        publish_douyin
        check_douyin_result
      fi
      ;;
    wechat_channels)
      echo "[${platform_name}] dialog_check"
      handle_wechat_channels_dialogs
      focus_platform_tab "$platform_name" >/dev/null
      echo "[${platform_name}] upload_start"
      upload_wechat_channels
      wechat_upload_result="$(poll_wechat_channels_upload)"
      echo "$wechat_upload_result"
      if json_failed "$wechat_upload_result"; then
        echo "[${platform_name}] upload_fallback_native_picker"
        upload_via_native_file_picker "$platform_name"
      fi
      echo "[${platform_name}] dialog_check"
      handle_wechat_channels_dialogs
      focus_platform_tab "$platform_name" >/dev/null
      echo "[${platform_name}] fill_start"
      fill_wechat_channels
      echo "[${platform_name}] description_start"
      fill_wechat_channels_description
      echo "[${platform_name}] cover_start"
      apply_wechat_channels_cover
      poll_wechat_channels_cover
      verify_wechat_channels_cover
      wait_for_wechat_channels_publish_ready
      if [[ "$SKIP_PUBLISH" == "false" ]]; then
        echo "[${platform_name}] publish_start"
        publish_wechat_channels
        check_wechat_channels_result
      fi
      ;;
    *)
      echo "Unsupported platform: $platform_name" >&2
      exit 1
      ;;
  esac

  focus_platform_tab "$platform_name" >/dev/null
}

if [[ "$PLATFORM" == "all" ]]; then
  run_platform xiaohongshu
  run_platform douyin
  run_platform wechat_channels
else
  run_platform "$PLATFORM"
fi
