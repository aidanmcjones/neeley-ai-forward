on run argv
	set theURL to item 1 of argv
	tell application "Google Chrome"
		set t to make new tab at end of tabs of window 1 with properties {URL:theURL}
		set i to 0
		repeat until (loading of t is false) or i > 40
			delay 0.5
			set i to i + 1
		end repeat
		delay 7
		set js1 to "(function(){var b=document.querySelector('[data-testid=triple-dot-dropdown]')||[...document.querySelectorAll('button')].find(e=>/other file options/i.test(e.getAttribute('aria-label')||''));if(!b)return 'nomenu';b.click();return 'menu';})()"
		set r1 to execute t javascript js1
		delay 2
		set js2 to "(function(){var els=[...document.querySelectorAll('[role=menuitem],button,a,li,div[role=option]')];var hit=els.find(e=>/^\\s*download/i.test((e.getAttribute('aria-label')||'')+(e.textContent||'').trim())||/download/i.test(e.getAttribute('data-testid')||''));if(!hit)return 'nodl';hit.click();return 'dl';})()"
		set r2 to "nodl"
		set j to 0
		repeat while (r2 is "nodl") and j < 10
			set r2 to execute t javascript js2
			if r2 is "nodl" then
				execute t javascript js1
				delay 1.5
			end if
			set j to j + 1
		end repeat
		set js3 to "(function(){var b=[...document.querySelectorAll('[role=dialog] button,[role=alertdialog] button')].find(x=>/original pdf/i.test(x.getAttribute('aria-label')||x.textContent));if(!b)return 'noconfirm';b.click();return 'confirmed';})()"
		set r3 to "noconfirm"
		set k to 0
		repeat while (r3 is "noconfirm") and k < 12
			delay 1.5
			set r3 to execute t javascript js3
			set k to k + 1
		end repeat
		delay 20
		set theTitle to title of t
		close t
		return r1 & " | " & r2 & " | " & r3 & " | " & theTitle
	end tell
end run
