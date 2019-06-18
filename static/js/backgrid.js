var grid;  // global

$(document).ready(function(){
    var continue_btn = "<button type='button' class='btn btn-small btn-link continue-btn'>Create NEW message to follow after this reply</button>";
    var link_msg_btn = "<button type='button' class='btn btn-small btn-link continue-btn'>Link EXISTING message to follow after this reply</button>";
    var delete_btn = "<button type='button' class='btn btn-small btn-link remove-btn'>Remove option</button>";

    // Ref: http://stackoverflow.com/questions/17444408/how-to-add-a-cutom-delete-option-for-backgrid-rows
    var DeleteCell = Backgrid.Cell.extend({

        template: _.template(delete_btn),
        events: {
            "click": "deleteRow"
        },
        deleteRow: function (e) {
            e.preventDefault();
            if(confirm('Are you sure you want to delete this option?')){
                this.model.collection.remove(this.model);
                row_count--; // defined in create_multiple_messages.html
                update_grid_height();
            }
        },
        render: function () {
            this.$el.html(this.template());
            this.delegateEvents();
            return this;
        }
    });

    var ContinueCell = Backgrid.Cell.extend({

        template: _.template(continue_btn),
        events: {
            "click": "continueOption"
        },
        continueOption: function (e) {
            e.preventDefault();
            if (this.model.attributes.child_msg_id) { // To prevent event being triggered when clicking empty cell
                submit(add_option_url, this.model.attributes.child_msg_id);
            }
        },
        render: function (e) {
            if (this.model.attributes.id) {
                this.$el.html(this.template());
            }
            else {
                // if this row has not been submitted, we'll not show the button
                this.$el.html('');
            }

            this.delegateEvents();
            return this;
        }
    });

    var LinkMessageCell = Backgrid.Cell.extend({ // link to another message from different campaign

        template: _.template(link_msg_btn),
        events: {
            "click": "linkMessages"
        },
        linkMessages: function (e) {
            e.preventDefault();
            if (this.model.attributes.child_msg_id) { // To prevent event being triggered when clicking empty cell
                submit(link_msg_url, this.model.attributes.child_msg_id, this.model.attributes.id);
            }
        },
        render: function (e) {
            if (this.model.attributes.id) {
                this.$el.html(this.template());
            }
            else {
                // if this row has not been submitted, we'll not show continue button
                this.$el.html('');
            }

            this.delegateEvents();
            return this;
        }
    });

    var Option = Backbone.Model.extend({});
    var Options = Backbone.Collection.extend({
        model: Option
    });

    var options = new Options();
    options.add(default_options);

    var separatorVals = [{name: 'Separators', values: [['None', ''], ['Space', ' '], [')', ')'], ['-', '-']]}];

    var columns = [{
        name: "keyword",
        label: "Allowed response aka KEYWORD",
        // The cell type can be a reference of a Backgrid.Cell subclass, any Backgrid.Cell subclass instances like *id* above, or a string
        cell: "string" // This is converted to "StringCell" and a corresponding class in the Backgrid package namespace is looked up
    }, {
        name: "separator",
        label: "Separating character",
        cell: Backgrid.SelectCell.extend({
            optionValues: separatorVals
        })
        //optionValues:  nums,
    }, {
        name: "option_text",
        label: "Text to appear after allowed reponse or KEYWORD (optional)",
        cell: "string" // An integer cell is a number cell that displays humanized integers
    }, {
        name: "exclude_option_text",
        label: "Exclude option text in the main message",
        //cell: "boolean",
        // this extension/fix is based on:
        // http://stackoverflow.com/questions/28368744/avoid-clicking-twice-to-begin-editing-boolean-checkbox-cell-in-backgrid
        cell: Backgrid.BooleanCell.extend({
            editor: Backgrid.BooleanCellEditor.extend({
                render: function () {
                    var model = this.model;
                    var columnName = this.column.get("name");
                    var val = this.formatter.fromRaw(model.get(columnName), model);

                    /*
                     * Toggle checked property since a click is what triggered enterEditMode
                     */
                    this.$el.prop("checked", !val);
                    model.set(columnName, !val);

                    return this;
                },
                defaults: {}
            })
        })
    }, {
        name: "notify",
        label: "Send text notification or alert on this response",
        cell: Backgrid.BooleanCell.extend({
            editor: Backgrid.BooleanCellEditor.extend({
                render: function () {
                    var model = this.model;
                    var columnName = this.column.get("name");
                    var val = this.formatter.fromRaw(model.get(columnName), model);

                    /*
                     * Toggle checked property since a click is what triggered enterEditMode
                     */
                    this.$el.prop("checked", !val);
                    model.set(columnName, !val);
                    return this;
                },
                defaults: {}
            })
        })
    }, {
        name: "wizard",
        label: "Queue for Wizard on this response",
        cell: Backgrid.BooleanCell.extend({
            editor: Backgrid.BooleanCellEditor.extend({
                render: function () {
                    var model = this.model;
                    var columnName = this.column.get("name");
                    var val = this.formatter.fromRaw(model.get(columnName), model);

                    /*
                     * Toggle checked property since a click is what triggered enterEditMode
                     */
                    this.$el.prop("checked", !val);
                    model.set(columnName, !val);
                    return this;
                },
                defaults: {}
            })
        })
    }, {
        name: "reply",
        label: "Our reply back",
        cell: "string" // A cell type for floating point value, defaults to have a precision 2 decimal numbers
    }, {
        name: "continue",
        label: "Action",
        cell: ContinueCell
    }, {
        name: "link",
        label: "Action",
        cell: LinkMessageCell
    }, {
        name: "delete",
        label: "Action",
        cell: DeleteCell
    }];

    // Initialize a new Grid instance
    grid = new Backgrid.Grid({
        columns: columns,
        collection: options,
        className: "table table-bordered"
    });

    // Render the grid and attach the root to your HTML document
    $("#backgrid-table").append(grid.render().el);
});
