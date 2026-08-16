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
                $("#onboard_result").html(renderSteps(d.steps) + '<div class="alert alert-success mt-2 mb-0">'+esc(d.message)+'</div>');
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
