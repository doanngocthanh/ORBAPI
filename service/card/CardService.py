
class CardService:
    """Service for managing card types"""
    
    CARD_TYPES = [
        {
            "id": 0,
            "name": "Thẻ Căn Cước Công Dân",
            "nameEn": "Citizens Card",
            "is_active": True
        },
        {
            "id": 1,
            "name": "Giấy Phép Lái Xe",
            "nameEn": "Driving License",
            "is_active": True
        },
       
        {
            "id": 3,
            "name": "Thẻ Ngân Hàng",
            "nameEn": "Bank Card",
            "is_active": True
        },
       
        {
            "id": 5,
            "name": "Thẻ Căn Cước Công Dân Mới",
            "nameEn": "New Citizens Card",
            "is_active": True
        },
        {
            "id": 6,
            "name": "Thẻ Chứng Minh Nhân Dân",
            "nameEn": "ID Card",
            "is_active": True
        },
        
    ]
    
    @classmethod
    def get_all_cards(cls):
        """Get all card types"""
        return cls.CARD_TYPES
    
    @classmethod
    def get_card_by_id(cls, card_id):
        """Get card type by ID"""
        for card in cls.CARD_TYPES:
            if card["id"] == card_id:
                return card
        return None
    
    @classmethod
    def get_active_cards(cls):
        """Get all active card types"""
        return [card for card in cls.CARD_TYPES if card["is_active"]]
    
class CardSideService:
    """Service for managing card sides"""
    
    CARD_SIDES = [
        {
            "id": 0,
            "name": "Mặt Trước",
            "nameEn": "Front",
            "is_active": True
        },
        {
            "id": 1,
            "name": "Mặt Sau",
            "nameEn": "Back",
            "is_active": True
        }
    ]
    
    @classmethod
    def get_all_sides(cls):
        """Get all card sides"""
        return cls.CARD_SIDES
    
    @classmethod
    def get_side_by_id(cls, side_id):
        """Get card side by ID"""
        for side in cls.CARD_SIDES:
            if side["id"] == side_id:
                return side
        return None
    
    @classmethod
    def get_active_sides(cls):
        """Get all active card sides"""
        return [side for side in cls.CARD_SIDES if side["is_active"]]



if __name__ == "__main__":
    # Example usage
    print("All Card Types:")
    for card in CardService.get_all_cards():
        print(card)
    
    print("\nActive Card Types:")
    for card in CardService.get_active_cards():
        print(card)
    
    print("\nCard Type with ID 1:")
    print(CardService.get_card_by_id(1))
    
    print("\nAll Card Sides:")
    for side in CardSideService.get_all_sides():
        print(side)
    
    print("\nActive Card Sides:")
    for side in CardSideService.get_active_sides():
        print(side)
    
    print("\nCard Side with ID 0:")
    print(CardSideService.get_side_by_id(0))