(function ($) {
    var csrf = document.getElementsByName('csrfmiddlewaretoken')[0].value;
    var local_path = window.location.pathname;
    function esc(s){ return $('<div>').text(s == null ? '' : String(s)).html(); }

    function isNum(x){ return /^-?\d+(\.\d+)?$/.test(String(x)); }

    // ---- meta: groups + providers for the form ----
    function loadMeta(cb){
        $.ajax({ url: local_path + 'manage/', type: 'POST', dataType: 'json',
            data: { csrfmiddlewaretoken: csrf, s: 'meta' },
            success: function(d){
                window.__meta = d;
                var g = (d.groups || []).slice().reverse().map(function(x){
                    return '<option value="'+esc(x)+'">'+esc(x)+'</option>'; }).join('');
                $('#gid_existing').html(g || '<option value="">(no groups — click + to add one)</option>');
                var p = (d.providers || []).map(function(x){
                    var sel = (x === d.default_provider) ? ' selected' : '';
                    return '<option value="'+esc(x)+'"'+sel+'>'+esc(x)+'</option>'; }).join('');
                $('#cl_provider').html(p || '<option value="">(no providers/connectors found)</option>');
                if (cb) cb(d);
            }
        });
    }

    // ---- list ----
    function loadClients(){
        $.ajax({ url: local_path + 'manage/', type: 'POST', dataType: 'json',
            data: { csrfmiddlewaretoken: csrf, s: 'list' },
            success: function(d){
                var list = d.clients || [];
                var out = $.map(list, function(c, i){
                    var login = c.has_password
                        ? '<span class="text-success" title="Password stored"><i class="fas fa-check-circle"></i></span>'
                        : '<span class="text-muted" title="No password stored — set one to share with the client"><i class="fas fa-minus-circle"></i></span>';
                    if (c.status === 'disabled') login += ' <span class="badge badge-secondary">disabled</span>';
                    var ips = (c.ips && c.ips.length)
                        ? c.ips.map(esc).join('<br>')
                        : '<span class="text-warning" title="Not whitelisted — client cannot bind in">— none —</span>';
                    var via = esc(c.provider) + (c.via_default ? ' <span class="badge badge-light" title="Falls through to the default route">default</span>' : '');
                    var fakeDlrBadge = '';
                    if (c.fake_dlr_percentage > 0) {
                        fakeDlrBadge = '<span class="badge badge-warning" title="'+esc(c.fake_dlr_percentage)+'% fake delivery reports">'+esc(c.fake_dlr_percentage)+'%</span>';
                    } else {
                        fakeDlrBadge = '<span class="text-muted">—</span>';
                    }
                    return '<tr>'
                        + '<td>'+(i+1)+'</td>'
                        + '<td><strong>'+esc(c.uid)+'</strong><div class="text-muted" style="font-size:12px;">'+esc(c.gid)+'</div></td>'
                        + '<td>'+esc(c.username)+'</td>'
                        + '<td class="text-center">'+login+'</td>'
                        + '<td style="font-size:12.5px;">'+ips+'</td>'
                        + '<td>'+via+'</td>'
                        + '<td class="text-right">'+esc(c.rate)+'</td>'
                        + '<td class="text-right">'+esc(c.balance)+' <span class="text-muted" style="font-size:11px;">'+esc(c.currency||'')+'</span></td>'
                        + '<td class="text-center">'+fakeDlrBadge+'</td>'
                        + '<td class="text-right">'+esc(c.today)+'</td>'
                        + '<td class="text-center" data-status-uid="'+esc(c.uid)+'"><i class="fas fa-circle-notch fa-spin text-muted" title="Checking…"></i></td>'
                        + '<td class="text-center"><div class="btn-group btn-group-sm">'
                        +   '<a href="javascript:void(0)" class="btn btn-light" title="Connection details" onclick="clientHandoff('+i+')"><i class="fas fa-paper-plane"></i></a>'
                        +   '<a href="javascript:void(0)" class="btn btn-light" title="Activity / logs" onclick="clientLogs('+i+')"><i class="fas fa-file-alt"></i></a>'
                        +   '<a href="javascript:void(0)" class="btn btn-light" title="Edit" onclick="clientEdit('+i+')"><i class="fas fa-edit"></i></a>'
                        +   '<a href="javascript:void(0)" class="btn btn-light" title="'+(c.status==='disabled'?'Enable':'Disable')+'" onclick="clientService('+i+')"><i class="fas fa-'+(c.status==='disabled'?'play':'ban')+'"></i></a>'
                        +   '<a href="javascript:void(0)" class="btn btn-light" title="Delete client" onclick="clientDelete('+i+')"><i class="fas fa-trash"></i></a>'
                        + '</div></td>'
                        + '</tr>';
                });
                $('#collectionlist').html(list.length ? out.join('') : $('.isEmpty').html());
                window.__clients = list;
                if (list.length) loadStatus(list.map(function(c){ return c.uid; }));
            },
            error: function(jqXHR){ if(window.quick_display_modal_error) quick_display_modal_error(jqXHR.responseText); }
        });
    }

    // ---- handoff text ----
    function handoffText(c){
        var ips = (c.ips && c.ips.length) ? c.ips.join(', ') : '(please send us the IP you will connect from)';
        return [
            'Client connection details — ' + (c.uid || ''),
            '',
            'Connect your SMPP client to OUR gateway:',
            '   Host / IP : ' + client_ctx.host,
            '   Port      : ' + client_ctx.port,
            '   System ID : ' + (c.username || ''),
            '   Password  : ' + (c.password || '(the password we set)'),
            '   Bind type : ' + (c.bind || 'transceiver'),
            '',
            'Your source IP (must stay whitelisted our side): ' + ips,
            '',
            'Once bound, send your SMS — we handle delivery through our provider.'
        ].join('\n');
    }
    function showHandoff(title, c, stepsHtml){
        $('#handoff_modal_title').text(title);
        $('#handoff_steps').html(stepsHtml || '');
        $('#handoff_text').text(handoffText(c));
        $('#handoff_modal').modal('show');
    }
    window.clientHandoff = function(i){
        var c = (window.__clients || [])[i]; if (!c) return;
        showHandoff('Connection details — ' + c.uid, c, '');
    };
    window.clientDelete = function(i){
        var c = (window.__clients || [])[i]; if (!c) return;
        sweetAlert({
            title: global_trans['areyousuretodelete'],
            text: 'Remove client "' + c.uid + '" — login, filter, route and whitelist entry?',
            type: 'warning', showCancelButton: true,
            cancelButtonClass: 'btn btn-secondary m-btn m-btn--pill m-btn--icon',
            cancelButtonText: global_trans['no'],
            confirmButtonClass: 'btn btn-danger m-btn m-btn--pill m-btn--air m-btn--icon',
            confirmButtonText: global_trans['yes'],
        }, function(ok){
            if (!ok) return;
            $.ajax({ url: local_path + 'manage/', type: 'POST',
                data: { csrfmiddlewaretoken: csrf, s: 'delete', uid: c.uid },
                success: function(d){ toastr.success(d.message, {closeButton:true, progressBar:true}); loadClients(); },
                error: function(jqXHR){ toastr.error(JSON.parse(jqXHR.responseText).message, {closeButton:true, progressBar:true}); }
            });
        });
    };

    // ---- live bound-in status ----
    function loadStatus(uids){
        $.ajax({ url: local_path + 'manage/', type: 'POST', dataType: 'json',
            data: { csrfmiddlewaretoken: csrf, s: 'status', uids: uids.join(',') },
            success: function(d){
                var m = d.status_map || {};
                $('[data-status-uid]').each(function(){
                    var st = m[$(this).attr('data-status-uid')] || {bound:false, detail:'Not bound in'};
                    var cls = st.bound ? 'text-success' : 'text-secondary';
                    $(this).html('<i class="fas fa-circle '+cls+'" title="'+esc(st.detail)+'"></i>');
                });
            },
            error: function(){ $('[data-status-uid]').html('<i class="fas fa-circle text-muted" title="unknown"></i>'); }
        });
    }

    // ---- activity / logs ----
    var logsUid = null;
    function loadLogs(){
        if (!logsUid) return;
        $.ajax({ url: local_path + 'manage/', type: 'POST', dataType: 'json',
            data: { csrfmiddlewaretoken: csrf, s: 'logs', uid: logsUid },
            success: function(d){
                var $b = $('#logs_bound').removeClass('alert-success alert-secondary');
                $b.addClass(d.bound ? 'alert-success' : 'alert-secondary')
                  .html('<i class="fas fa-'+(d.bound?'check-circle':'circle')+' mr-1"></i>'+esc(d.detail || (d.bound?'Bound in':'Not bound in')));
                var rows = (d.rows || []).map(function(r){
                    return '<tr><td>'+esc(r.at)+'</td><td>'+esc(r.cid)+'</td><td>'+esc(r.status)+'</td><td>'+esc(r.msgid)+'</td></tr>';
                }).join('');
                $('#logs_rows').html(rows || '<tr><td colspan="4" class="text-muted">No messages logged for this client yet.</td></tr>');
            }
        });
    }
    window.clientLogs = function(i){
        var c = (window.__clients || [])[i]; if (!c) return;
        logsUid = c.uid;
        $('#logs_title').text('Activity — ' + c.uid);
        $('#logs_bound').removeClass('alert-success alert-secondary').addClass('alert-secondary').text('Loading…');
        $('#logs_rows').html('<tr><td colspan="4" class="text-muted">Loading…</td></tr>');
        loadLogs();
        $('#logs_modal').modal('show');
    };
    $('#logs_refresh').on('click', loadLogs);

    // ---- enable / disable ----
    window.clientService = function(i){
        var c = (window.__clients || [])[i]; if (!c) return;
        var disable = (c.status !== 'disabled');
        $.ajax({ url: local_path + 'manage/', type: 'POST',
            data: { csrfmiddlewaretoken: csrf, s: 'service', uid: c.uid, action: disable ? 'disable' : 'enable' },
            success: function(d){ toastr.success(d.message, {closeButton:true, progressBar:true}); loadClients(); },
            error: function(jqXHR){ toastr.error(JSON.parse(jqXHR.responseText).message, {closeButton:true, progressBar:true}); }
        });
    };

    // ---- edit (pre-filled with current values) ----
    function buildEdProvider(c){
        var provs = (window.__meta && window.__meta.providers) || [];
        if (provs.indexOf(c.provider) === -1 && c.provider && c.provider !== '—') provs = provs.concat([c.provider]);
        $('#ed_provider').html(provs.map(function(x){
            return '<option value="'+esc(x)+'"'+(x===c.provider?' selected':'')+'>'+esc(x)+'</option>';
        }).join(''));
    }
    window.clientEdit = function(i){
        var c = (window.__clients || [])[i]; if (!c) return;
        $('#edit_form')[0].reset();
        $('#ed_uid').val(c.uid);
        $('#edit_title').text('Edit client — ' + c.uid);
        $('#ed_password').val('');                                   // never prefilled
        $('#ed_rate').val(isNum(c.rate) ? c.rate : '');
        $('#ed_balance').val(isNum(c.balance) ? c.balance : '');     // ND -> blank
        $('#ed_throughput').val(isNum(c.throughput) ? c.throughput : '');
        $('#ed_fake_dlr').val(c.fake_dlr_percentage || 0);
        $('#ed_ips').val('');
        $('#ed_ips_current').text((c.ips && c.ips.length) ? ('Currently whitelisted: ' + c.ips.join(', ')) : 'No IP whitelisted yet.');
        if (window.__meta) buildEdProvider(c); else loadMeta(function(){ buildEdProvider(c); });
        $('#edit_modal').modal('show');
    };
    $('#edit_form').on('submit', function(e){
        e.preventDefault();
        var $btn = $('#edit_submit').prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-1"></i>Saving…');
        $.ajax({ url: local_path + 'manage/', type: 'POST', dataType: 'json',
            data: $(this).serialize() + '&s=edit',
            success: function(d){
                toastr.success(d.message, {closeButton:true, progressBar:true});
                $('#edit_modal').modal('hide'); loadClients();
                $btn.prop('disabled', false).html('<i class="fas fa-save mr-1"></i>Save changes');
            },
            error: function(jqXHR){
                var r={}; try{ r=JSON.parse(jqXHR.responseText); }catch(e){}
                toastr.error(r.message || 'Failed', {closeButton:true, progressBar:true});
                $btn.prop('disabled', false).html('<i class="fas fa-save mr-1"></i>Save changes');
            }
        });
    });

    function stepsHtml(steps){
        return (steps || []).map(function(s){
            var ic = s.ok ? '<i class="fas fa-check-circle text-success mr-1"></i>'
                          : '<i class="fas fa-exclamation-circle text-warning mr-1"></i>';
            return '<div style="font-size:13px;">'+ic+'<strong>'+esc(s.step)+'</strong> — '+esc(s.detail)+'</div>';
        }).join('');
    }

    // ---- group toggle ----
    $('#gid_toggle').on('click', function(){
        var showNew = $('#gid_new').is(':visible');
        $('#gid_new').toggle(!showNew);
        $('#gid_existing').toggle(showNew);
    });

    // ---- create ----
    $('#add_new_obj').on('click', function(){ $('#client_form')[0].reset(); loadMeta(); $('#gid_new').hide(); $('#gid_existing').show(); $('#collection_modal').modal('show'); });
    $('#client_form').on('submit', function(e){
        e.preventDefault();
        var newGroup = $('#gid_new').is(':visible');
        var data = {
            csrfmiddlewaretoken: csrf, s: 'create',
            uid: $('input[name=uid]').val(),
            username: $('#cl_username').val(),
            password: $('#cl_password').val(),
            group_mode: newGroup ? 'new' : 'existing',
            gid: newGroup ? $('#gid_new').val() : $('#gid_existing').val(),
            provider: $('#cl_provider').val(),
            rate: $('input[name=rate]').val(),
            ips: $('input[name=ips]').val(),
            currency: $('select[name=currency]').val(),
            balance: $('input[name=balance]').val(),
            throughput: $('input[name=throughput]').val(),
            fake_dlr_percentage: $('#cl_fake_dlr').val() || '0'
        };
        var $btn = $('#client_submit').prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-1"></i>Working…');
        $.ajax({ url: local_path + 'manage/', type: 'POST', dataType: 'json', data: data,
            success: function(d){
                toastr.success(d.message, {closeButton:true, progressBar:true});
                $('#collection_modal').modal('hide');
                loadClients();
                var h = d.handoff || {};
                h.uid = h.uid || data.uid;
                showHandoff('Client created — ' + h.uid, h, stepsHtml(d.steps));
                $btn.prop('disabled', false).html('<i class="fas fa-plus mr-1"></i>Create client');
            },
            error: function(jqXHR){
                var r = {}; try { r = JSON.parse(jqXHR.responseText); } catch(e){}
                toastr.error(r.message || 'Failed', {closeButton:true, progressBar:true});
                $('#client_form').prepend('');
                $btn.prop('disabled', false).html('<i class="fas fa-plus mr-1"></i>Create client');
            }
        });
    });

    // ---- copy handoff ----
    function fallbackCopy(text){
        var ta = document.createElement('textarea');
        ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); } catch(e){}
        document.body.removeChild(ta);
    }
    $('#handoff_copy').on('click', function(){
        var text = $('#handoff_text').text();
        var done = function(){ toastr.success('Copied — send it to the client.', {timeOut:2500}); };
        if (navigator.clipboard && navigator.clipboard.writeText){
            navigator.clipboard.writeText(text).then(done, function(){ fallbackCopy(text); done(); });
        } else { fallbackCopy(text); done(); }
    });

    loadClients();
    $('li.nav-item.clients-menu').addClass('active');
})(jQuery);
