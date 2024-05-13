import {Sense} from "./sense.js";

export class LiteralSense extends Sense {

    // Handles extra info of literals (root, related to)
    constructor(sense) {
        super(sense);
        this.label = 'Literal'
        this.insane = true
    }

    set_colour() {
        this.row.style.backgroundColor = '#EEE6E4'
    }

    fill_relation_cell() {
        this.relation_cell.innerHTML = ''
        let span = document.createElement('span')
        span.style.opacity = '0.5'
        span.innerHTML = 'N/A'
        this.relation_cell.appendChild(span)
    }
}