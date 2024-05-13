import {LiteralSense} from "./literal_sense.js";
import {MetaphoricalSense} from "./metaphorical_sense.js";

export class RelatedSense extends LiteralSense {

    constructor(sense) {
        super(sense);
        if (!(sense instanceof RelatedSense)) {
            this.resembles = null
        } else {
            this.resembles = sense.resembles
        }
        this.label = 'Related'
        this.systematic = null
    }

    set_colour() {
        this.row.style.backgroundColor = '#FFF1DE'
    }

    get_systematic() {
        this.sanify()
        return this.systematic
    }

    issues() {
        let issues = super.issues()
        if (this.get_resembles() === null) {
            issues.add_issue(`${this.get_outward_facing_id()} is not connected to another sense.`)
        }
        /*
        if (this.get_systematic() === null) {
            issues.add_issue(`${this.get_outward_facing_id()} is not labelled as regular or irregular.`)
        }*/
        return issues
    }

    sanify() {
        if (this.insane) {
            super.sanify()
            this.insane = true

            // Make sure the thing it resembles is a literal root
            let resembles_sense = null
            if (this.resembles !== null) {
                resembles_sense = this.lemma.get_sense(this.resembles)

                if (!this.lemma.new_id_order.includes(this.resembles)) {
                    this.resembles = null
                } else if (!(this.is_valid_connection(resembles_sense))) {
                    this.resembles = null
                }
            }

            if (this.resembles === null) {
                this.systematic = null
            }
            this.insane = false
        }
    }


    get_resembles() {
        this.sanify()
        return this.resembles
    }

    set_resembles(sense_id) {
        if (this.resembles !== sense_id) {
            this.resembles = sense_id
            this.systematic = null
            this.insane = true
            this.lemma.refresh()
        }
    }

    set_systematic(bool) {
        if (bool !== this.systematic) {
            this.systematic = bool
            this.insane = true
            this.lemma.refresh()
        }
    }

    get_data() {
        let sense_data = super.get_data()
        sense_data['connected_to'] = this.lemma.get_sense(this.get_resembles()).get_backend_sense_id()
        // sense_data['is_regular'] = this.get_systematic()
        return sense_data
    }

    update_resembles() {
        const dropdown = document.getElementById(`${this.new_sense_id}:resemblance_select`)
        this.set_resembles(dropdown.value)
        console.log(`${this.new_sense_id} resembles ${this.resembles}`)
        this.lemma.refresh()
    }

    is_valid_connection(other_sense) {
        return ((other_sense instanceof LiteralSense && (!(other_sense instanceof RelatedSense)))||
            ((other_sense instanceof MetaphoricalSense || other_sense instanceof RelatedSense) && other_sense.is_subcore() && other_sense.new_sense_id !== this.new_sense_id))
    }

    fill_relation_cell() {
        // Make dropdown selection
        this.relation_cell.innerHTML = ''

        let resemblance_cell = document.createElement('nobr')
        // resemblance_cell.innerHTML = 'Connects to '

        let select_resemblance = document.createElement("select");
        select_resemblance.id = `${this.new_sense_id}:resemblance_select`
        let that = this
        select_resemblance.onchange = function(){
            that.lemma.screen.logs.log('connect', that.get_backend_sense_id(), that.lemma.get_sense(document.getElementById(`${that.new_sense_id}:resemblance_select`).value).get_backend_sense_id())
            that.update_resembles()
        }

        let blank_option = document.createElement("option");
        blank_option.value = null
        blank_option.disabled = true
        blank_option.hidden = true
        blank_option.innerHTML = 'select';
        select_resemblance.appendChild(blank_option)

        // Add options
        let found_resembles = false
        if (this.get_resembles() === null) {
            blank_option.selected = true
            found_resembles = true
        }
        for (const other_sense of this.lemma.all_senses()) {
            const other_sense_id = other_sense.new_sense_id
            let option = document.createElement("option");
            option.value = other_sense_id;
            option.text = other_sense.get_outward_facing_id();
            if (this.is_valid_connection(other_sense)) {
                if (other_sense_id === this.get_resembles()) {
                    // Select
                    option.selected = true
                    found_resembles = true
                }
            } else {
                // Hide
                option.disabled = true
            }
            select_resemblance.appendChild(option);
        }
        if (!found_resembles) {
            console.error(`Failed to find resembled (${this.new_sense_id} resembles ${this.get_resembles()})`)
        }

        resemblance_cell.appendChild(select_resemblance)
        this.relation_cell.appendChild(resemblance_cell)
        this.relation_cell.appendChild(document.createElement('br'))

        // Add ad-hoc vs. systematic choice
        /*
        if (this.get_resembles() !== null) {

            const systematicity_name = `${this.new_sense_id}:systematicity`

            let systematicity = document.createElement('span')
            for (const [option, bool] of [['Regular', true], ['Irregular', false]]) {

                const name = `${systematicity_name}:${option}`

                let line = document.createElement('nobr')

                // Select box
                let checkbox = document.createElement('input')
                checkbox.type = 'radio'
                checkbox.name = systematicity_name
                checkbox.id = name
                checkbox.onclick = function () {
                    that.set_systematic(bool)
                }
                line.appendChild(checkbox)

                // Label
                let label = document.createElement("label");
                label.htmlFor = name
                label.innerHTML = option
                line.appendChild(label)

                if (this.get_systematic() === bool) {
                    checkbox.checked = true
                } else if (this.get_systematic() !== null) {
                    label.style.opacity = '0.5'
                }

                // Linebreak
                line.appendChild(document.createElement("br"))

                systematicity.appendChild(line)
            }
            this.relation_cell.appendChild(systematicity)
        }*/
    }
}
