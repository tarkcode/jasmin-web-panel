(function($){
    var csrf = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    var USERS = {};
    function esc(s){ return $('<div>').text(s == null ? '' : String(s)).html(); }

    // Load existing groups + users (with stored credentials) for the pickers.
    $.ajax({ url: main_trans.url2onboard, type: "POST", dataType: "json",
        data: { csrfmiddlewaretoken: csrf, s: "meta" },
        success: function(d){
            var gopts = (d.groups || []).slice().reverse().map(function(g){
                return '<option value="'+esc(g)+'">'+esc(g)+'</option>';
            }).join('');
            $("#gid_existing").html(gopts || '<option value="">(no groups yet — choose "Create new")</option>');

            var uopts = (d.users || []).slice().reverse().map(function(u){
                return '<option value="'+esc(u.uid)+'">'+esc(u.uid)+' ('+esc(u.username)+')</option>';
            }).join('');
            $("#existing_uid").html(uopts || '<option value="">(no users yet)</option>');
            (d.users || []).forEach(function(u){ USERS[u.uid] = u; });
            updateNewUserSummary();
        }
    });

    // Fill the connector username/password from a selected existing user.
    function syncFromExistingUser(){
        var u = USERS[$("#existing_uid").val()];
        if (!u) return;
        $("#conn_username").val(u.username || "");
        if (u.password){
            $("#conn_password").val(u.password).attr('type', 'text');
            $("#existing_note").removeClass("text-warning").addClass("text-muted")
                .text("Username & password applied to the connector above.");
        } else {
            $("#conn_password").val("");
            $("#existing_note").removeClass("text-muted").addClass("text-warning")
                .text("This user's password isn't stored — type it above so the connector matches.");
        }
    }

    // Live "will be created as" summary for the new-user path, so the uid,
    // username (from the connector), password source and group are all visible.
    function currentGid(){
        return $('input[name=group_mode]:checked').val() === 'new'
            ? ($("#gid_new").val() || '—') : ($("#gid_existing").val() || '—');
    }
    function updateNewUserSummary(){
        var uid = $("#uid_new").val() || '—';
        var uname = $("#conn_username").val() || '—';
        var pw = $("#conn_password").val() ? 'same as connector' : 'not set yet';
        $("#new_user_summary").html(
            'Will create user <strong>' + esc(uid) + '</strong> — login username <strong>' + esc(uname) +
            '</strong>, password <strong>' + pw + '</strong>, group <strong>' + esc(currentGid()) + '</strong>.'
        );
    }

    $('input[name=user_mode]').on('change', function(){
        if ($(this).val() === 'existing'){
            $("#usr_new_wrap").hide(); $("#usr_existing_wrap").show(); $("#group_section").hide();
            syncFromExistingUser();
        } else {
            $("#usr_existing_wrap").hide(); $("#usr_new_wrap").show(); $("#group_section").show();
            updateNewUserSummary();
        }
    });
    $("#existing_uid").on('change', syncFromExistingUser);
    $("#uid_new, #conn_username, #conn_password, #gid_new").on('input', updateNewUserSummary);
    $("#gid_existing").on('change', updateNewUserSummary);

    $('input[name=group_mode]').on('change', function(){
        if ($(this).val() === 'new'){ $("#gid_existing").hide(); $("#gid_new").show(); }
        else { $("#gid_new").hide(); $("#gid_existing").show(); }
        updateNewUserSummary();
    });

    $("#make_route").on('change', function(){ $("#rate_wrap").toggle(this.checked); });

    $(document).on('click', '.toggle-password', function(e){
        e.preventDefault();
        var $i = $(this).closest('.input-group').find('.password-input');
        var $ic = $(this).find('i');
        if ($i.attr('type') === 'password'){ $i.attr('type', 'text'); $ic.removeClass('fa-eye').addClass('fa-eye-slash'); }
        else { $i.attr('type', 'password'); $ic.removeClass('fa-eye-slash').addClass('fa-eye'); }
    });

    function renderSteps(steps){
        return (steps || []).map(function(s){
            var icon = s.ok
                ? '<i class="fas fa-check-circle text-success mr-1"></i>'
                : '<i class="fas fa-times-circle text-danger mr-1"></i>';
            return '<div class="step-line">'+icon+'<strong>'+esc(s.step)+'</strong> — '+esc(s.detail)+'</div>';
        }).join('');
    }
    // Copy-ready message for the provider, so exact IP/port/system_id/password
    // get sent — never a mismatch. Covers both directions (we dial them / they
    // bind into us); the operator trims the one that doesn't apply.
    function buildHandoffText(h){
        return [
            "SMPP connection details — " + h.cid,
            "",
            "Bind type: " + h.bind,
            "",
            "1) If WE connect to YOUR SMSC (this connector dials out to you):",
            "   - Please whitelist our server IP:  " + h.our_host,
            "   - We connect to your server:       " + h.their_host + ":" + h.their_port,
            "   - System ID (username):            " + h.system_id,
            "   - Password:                        " + h.password,
            "",
            "2) Or, if YOU bind INTO our gateway instead:",
            "   - Host / IP:  " + h.our_host,
            "   - Port:       " + h.our_port,
            "   - System ID:  " + h.system_id,
            "   - Password:   " + h.password,
            "   - Our server is IP-restricted; send us the source IP you connect from so we whitelist it.",
            "",
            "Please confirm which direction applies and that the account is active."
        ].join("\n");
    }
    function renderHandoff(h){
        if(!h) return "";
        return '<div class="card border-info mt-3">'
            + '<div class="card-header py-2 d-flex justify-content-between align-items-center">'
            +   '<span><i class="fas fa-paper-plane mr-1"></i>Message for the provider</span>'
            +   '<button type="button" class="btn btn-sm btn-outline-primary" id="handoff_copy"><i class="far fa-copy mr-1"></i>Copy</button>'
            + '</div>'
            + '<div class="card-body p-0"><pre id="handoff_text" style="white-space:pre-wrap;word-break:break-word;margin:0;padding:12px;font-size:12.5px;line-height:1.5;">'
            + esc(buildHandoffText(h)) + '</pre></div></div>';
    }
    function fallbackCopy(text){
        var ta = document.createElement('textarea');
        ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); } catch(e){}
        document.body.removeChild(ta);
    }
    $(document).on('click', '#handoff_copy', function(){
        var text = $("#handoff_text").text();
        var done = function(){ toastr.success('Copied — paste it to the provider.', { timeOut: 2500 }); };
        if (navigator.clipboard && navigator.clipboard.writeText){
            navigator.clipboard.writeText(text).then(done, function(){ fallbackCopy(text); done(); });
        } else { fallbackCopy(text); done(); }
    });
    function resetBtn($btn){ $btn.prop('disabled', false).html('<i class="fas fa-plus mr-1"></i>Create'); }

    $("#onboard_form").on('submit', function(e){
        e.preventDefault();
        var mode = $('input[name=user_mode]:checked').val();
        var gmode = $('input[name=group_mode]:checked').val();
        var payload = {
            csrfmiddlewaretoken: csrf, s: "create",
            cid: $("input[name=cid]").val(), host: $("input[name=host]").val(), port: $("input[name=port]").val(),
            username: $("#conn_username").val(), password: $("#conn_password").val(),
            user_mode: mode, uid: $("#uid_new").val(), existing_uid: $("#existing_uid").val(),
            group_mode: gmode, gid: (gmode === 'new' ? $("#gid_new").val() : $("#gid_existing").val()),
            make_route: $("#make_route").is(":checked") ? "true" : "false", rate: $("#rate").val()
        };
        var $btn = $("#onboard_submit").prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-1"></i>Working…');
        $("#onboard_result").html('<div class="text-muted"><i class="fas fa-spinner fa-spin mr-1"></i>Creating…</div>');
        $.ajax({ url: main_trans.url2onboard, type: "POST", data: payload, dataType: "json",
            success: function(d){
                $("#onboard_result").html(
                    renderSteps(d.steps)
                    + '<div class="alert alert-success mt-2 mb-1">'+esc(d.message)+'</div>'
                    + renderHandoff(d.handoff)
                );
                toastr.success(d.message, { closeButton: true, progressBar: true });
                resetBtn($btn);
            },
            error: function(jqXHR){
                var r = {};
                try { r = JSON.parse(jqXHR.responseText); } catch (err) {}
                $("#onboard_result").html(renderSteps(r.steps) + '<div class="alert alert-danger mt-2 mb-0">'+esc(r.message || 'Failed')+'</div>');
                toastr.error(r.message || 'Failed', { closeButton: true, progressBar: true });
                resetBtn($btn);
            }
        });
    });

    updateNewUserSummary();
    $("li.nav-item.onboard-menu").addClass("active");
})(jQuery);
