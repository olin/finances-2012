function FitToContent(id, maxHeight)
{
   var text = id && id.style ? id : document.getElementById(id);
   if ( !text )
      return;

   var adjustedHeight = text.clientHeight;
   if ( !maxHeight || maxHeight > adjustedHeight )
   {
      adjustedHeight = Math.max(text.scrollHeight, adjustedHeight);
      if ( maxHeight )
         adjustedHeight = Math.min(maxHeight, adjustedHeight);
      if ( adjustedHeight > text.clientHeight )
         text.style.height = adjustedHeight + "px";
   }
}

$(function () {
	var form_open = window.location.search.substring(1)

	/* club view */
	if ($('body').hasClass('group')) {
		/*
		$.each(["budget-form", "revenue-form"], function (_, form_id) {
			var form = $('#' + form_id)
			form.attr('action', "?" + form_id)

			var button = $(document.createElement('button')).insertBefore(form)
			button.html('Insert Expense').css('position', 'absolute')

			button.click(function () {
				button.hide()
				form.show()
				$('input[type="text"]:first', form).focus()
			})
			$('input[type="reset"]', form).click(function () {
				form.hide()
				button.show()
			})

			if (form_open == form_id) {
				button.hide()
				$('input[type="text"]:first', form).focus()
			} else
				form.hide()
		})
		*/

		$('select[name="type"]').change(function () {
			var students = $(this).next('select[name="student"]')
			this.value == "reimbursement" ? students.show() : students.hide()
		}).keyup(function () { $(this).change(); }).change()

		$('input.delete-button').click(function () {
			return confirm('Are you sure you want to delete this item?')
		})
	}

	function addMassEditControls(form, isEmpty) {
		// isolate prototype row
		var table = $('table', form)
		var input_row = $('tr:eq(1)', form)
		var header = $('tr:eq(0)', form)
		// remove extraneous rows
		$('tr:gt(0)', form).remove()
		table.append(input_row.clone())
		var row_count = 1

		// add buttons
		var add_row = $(document.createElement('input')).attr('type', 'button').val('Add Entry')
		add_row.prependTo($('div.table-form-submit', form))
		var delete_row = $(document.createElement('input')).attr('type', 'button').val('Remove Entry')
		delete_row.insertAfter(add_row).before(" ").after(" ")
		delete_row.attr('disabled', true)

		add_row.click(function () {
			input_row.clone().appendTo(table).find('td:first > :first-child').focus()
			row_count += 1
			if (row_count > 1)
				delete_row.removeAttr('disabled')
		})
		delete_row.click(function () {
			var row = $('tr:last', table)
			if (!isEmpty(row))
				if (!confirm('Are you sure you want to remove this entry?'))
					return;
			$('tr:last', table).remove()
			row_count -= 1
			if (row_count <= 1)
				delete_row.attr('disabled', true)
		})
		form.submit(function () {
			/* here we should validate form */
		})
	}

	/* reimbursement view */
	if ($('body').hasClass('reimbursements')) {
		addMassEditControls($('#reimbursements-form'),
			function isEmpty(row) {
				return row.find('select:eq(0)').val() == -1 && row.find('select:eq(1)').val() == -1
			})

		$('form[action="/reimbursements/mark"]').submit(function () {
			if (!confirm('Are you sure you are finished with these reimbursements?'))
				return false;
		})
	}

	/* transactions view */
	if ($('body').hasClass('transactions')) {
		addMassEditControls($('#transactions-form'),
			function isEmpty(row) {
				return row.find('select:eq(0)').val() == -1 && row.find('select:eq(1)').val() == -1
			})

		$('form[action="/transactions/mark"]').submit(function () {
			if (!confirm('Are you sure you are finished with these transactions?'))
				return false;
		})
	}

	/* clubs view */
	if ($('body').hasClass('groups')) {
		addMassEditControls($('#clubs-form'),
			function isEmpty(row) {
				return !row.find('input:eq(0)').val()
			})
	}
})
