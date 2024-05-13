export function make_empty_cell() {
    let cell = document.createElement("td")
    cell.style.padding = `0 10px`
    return cell
}

export function is_valid_feature(feature_string) {
    if (feature_string.length === 0) {
        return false
    }
    for (const forbidden_char of ['.', '#', '$', '/', '[', ']']) {
        if (feature_string.includes(forbidden_char)) {
            return false
        }
    }
    return true
}